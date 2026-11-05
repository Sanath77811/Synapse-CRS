"""Z3 policy checks for recommendation-only decision proposals."""

from uuid import uuid4

from z3 import And, Bool, Implies, Not, Solver, sat, unsat

from synapse_reasoning import POLICY_VERSION
from synapse_reasoning.models import (
    DecisionProposal,
    ProposalKind,
    Reconstruction,
    VerificationResult,
)

SOLVER_NAME = "z3"
TIMEOUT_MS = 2000

CONSTRAINTS = (
    "executed_is_false",
    "destructive_is_false",
    "authorized",
    "in_scope",
    "identity_certain",
    "evidence_present",
    "human_approval_if_impactful",
    "mitigation_kind_forbidden",
)


def propose(
    reconstruction: Reconstruction,
    kind: ProposalKind,
    *,
    authorized: bool,
    in_scope: bool,
    human_approved: bool,
) -> DecisionProposal:
    impactful = kind in {"recommend_isolate_lab_target", "execute_host_mitigation"}
    destructive = kind == "execute_host_mitigation"
    evidence_present = len(reconstruction.observations) >= 1
    identity_certain = reconstruction.quality.identity_verification >= 1.0 and not any(
        "process_started" in item.missing for item in reconstruction.processes
    )
    return DecisionProposal(
        proposal_id=uuid4(),
        kind=kind,
        target_id=reconstruction.target_id,
        authorized=authorized,
        in_scope=in_scope,
        identity_certain=identity_certain,
        evidence_present=evidence_present,
        human_approved=human_approved,
        destructive=destructive,
        impactful=impactful,
        executed=False,
        rationale=f"Recommendation record only: {kind}",
    )


def verify_proposal(proposal: DecisionProposal) -> VerificationResult:
    solver = Solver()
    solver.set("timeout", TIMEOUT_MS)
    authorized = Bool("authorized")
    in_scope = Bool("in_scope")
    identity_certain = Bool("identity_certain")
    evidence_present = Bool("evidence_present")
    human_approved = Bool("human_approved")
    destructive = Bool("destructive")
    impactful = Bool("impactful")
    executed = Bool("executed")
    mitigation = Bool("mitigation_kind")
    solver.add(authorized == proposal.authorized)
    solver.add(in_scope == proposal.in_scope)
    solver.add(identity_certain == proposal.identity_certain)
    solver.add(evidence_present == proposal.evidence_present)
    solver.add(human_approved == proposal.human_approved)
    solver.add(destructive == proposal.destructive)
    solver.add(impactful == proposal.impactful)
    solver.add(executed == proposal.executed)
    solver.add(mitigation == (proposal.kind == "execute_host_mitigation"))
    policy = And(
        Not(executed),
        Not(destructive),
        authorized,
        in_scope,
        identity_certain,
        evidence_present,
        Implies(impactful, human_approved),
        Not(mitigation),
    )
    solver.add(policy)
    result = solver.check()
    if result == sat:
        status = "verified_under_model"
        solver_result: str = "sat"
        violated: tuple[str, ...] = ()
        missing = ()
        explanation = "SAT under encoded policy. This is not a proof of real-world safety."
    elif result == unsat:
        status = "rejected_by_policy"
        solver_result = "unsat"
        violated = _violations(proposal)
        missing = tuple(name for name in violated if name.endswith("present") or "certain" in name)
        explanation = "UNSAT: the encoded safety policy is not satisfied."
    else:
        status = "not_verified"
        solver_result = "unknown"
        violated = ()
        missing = ()
        explanation = "Solver returned unknown (timeout or incomplete result)."
    if not proposal.evidence_present and status != "verified_under_model":
        status = "unknown_insufficient_evidence"
    return VerificationResult(
        proposal_id=proposal.proposal_id,
        policy_version=POLICY_VERSION,
        status=status,  # type: ignore[arg-type]
        solver_result=solver_result,  # type: ignore[arg-type]
        constraints=CONSTRAINTS,
        violated=violated,
        missing_preconditions=missing,
        solver=f"{SOLVER_NAME} timeout_ms={TIMEOUT_MS}",
        explanation=explanation,
        assumptions=(
            "Policy 1.0.0 encodes authorization, scope, enrolled identity, "
            "non-execution, and a ban on host mitigation in this phase."
        ),
    )


def _violations(proposal: DecisionProposal) -> tuple[str, ...]:
    failed = []
    if proposal.executed:
        failed.append("executed_is_false")
    if proposal.destructive:
        failed.append("destructive_is_false")
    if not proposal.authorized:
        failed.append("authorized")
    if not proposal.in_scope:
        failed.append("in_scope")
    if not proposal.identity_certain:
        failed.append("identity_certain")
    if not proposal.evidence_present:
        failed.append("evidence_present")
    if proposal.impactful and not proposal.human_approved:
        failed.append("human_approval_if_impactful")
    if proposal.kind == "execute_host_mitigation":
        failed.append("mitigation_kind_forbidden")
    return tuple(failed)
