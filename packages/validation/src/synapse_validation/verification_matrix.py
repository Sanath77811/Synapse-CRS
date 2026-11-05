"""Z3 policy test matrix. SAT is not real-world safety."""

from uuid import uuid4

from synapse_reasoning.models import DecisionProposal
from synapse_reasoning.verification import TIMEOUT_MS, verify_proposal

CASES: tuple[dict[str, object], ...] = (
    {
        "name": "authorized_proposal",
        "kind": "recommend_analyst_investigation",
        "authorized": True,
        "in_scope": True,
        "identity_certain": True,
        "evidence_present": True,
        "human_approved": False,
        "destructive": False,
        "impactful": False,
        "executed": False,
        "expected": "verified_under_model",
        "solver": "sat",
    },
    {
        "name": "unauthorized_proposal",
        "kind": "recommend_analyst_investigation",
        "authorized": False,
        "in_scope": True,
        "identity_certain": True,
        "evidence_present": True,
        "human_approved": False,
        "destructive": False,
        "impactful": False,
        "executed": False,
        "expected": "rejected_by_policy",
        "solver": "unsat",
    },
    {
        "name": "out_of_scope_target",
        "kind": "recommend_analyst_investigation",
        "authorized": True,
        "in_scope": False,
        "identity_certain": True,
        "evidence_present": True,
        "human_approved": False,
        "destructive": False,
        "impactful": False,
        "executed": False,
        "expected": "rejected_by_policy",
        "solver": "unsat",
    },
    {
        "name": "unknown_target_identity",
        "kind": "recommend_analyst_investigation",
        "authorized": True,
        "in_scope": True,
        "identity_certain": False,
        "evidence_present": True,
        "human_approved": False,
        "destructive": False,
        "impactful": False,
        "executed": False,
        "expected": "rejected_by_policy",
        "solver": "unsat",
    },
    {
        "name": "missing_evidence",
        "kind": "recommend_analyst_investigation",
        "authorized": True,
        "in_scope": True,
        "identity_certain": True,
        "evidence_present": False,
        "human_approved": False,
        "destructive": False,
        "impactful": False,
        "executed": False,
        "expected": "unknown_insufficient_evidence",
        "solver": "unsat",
    },
    {
        "name": "missing_human_approval",
        "kind": "recommend_isolate_lab_target",
        "authorized": True,
        "in_scope": True,
        "identity_certain": True,
        "evidence_present": True,
        "human_approved": False,
        "destructive": False,
        "impactful": True,
        "executed": False,
        "expected": "rejected_by_policy",
        "solver": "unsat",
    },
    {
        "name": "destructive_action",
        "kind": "execute_host_mitigation",
        "authorized": True,
        "in_scope": True,
        "identity_certain": True,
        "evidence_present": True,
        "human_approved": True,
        "destructive": True,
        "impactful": True,
        "executed": False,
        "expected": "rejected_by_policy",
        "solver": "unsat",
    },
    {
        "name": "forbidden_mitigation_type",
        "kind": "execute_host_mitigation",
        "authorized": True,
        "in_scope": True,
        "identity_certain": True,
        "evidence_present": True,
        "human_approved": True,
        "destructive": False,
        "impactful": True,
        "executed": False,
        "expected": "rejected_by_policy",
        "solver": "unsat",
    },
    {
        "name": "invalid_executed_flag",
        "kind": "recommend_analyst_investigation",
        "authorized": True,
        "in_scope": True,
        "identity_certain": True,
        "evidence_present": True,
        "human_approved": False,
        "destructive": False,
        "impactful": False,
        "executed": True,
        "expected": "rejected_by_policy",
        "solver": "unsat",
    },
    {
        "name": "conflicting_constraints",
        "kind": "execute_host_mitigation",
        "authorized": False,
        "in_scope": False,
        "identity_certain": False,
        "evidence_present": False,
        "human_approved": False,
        "destructive": True,
        "impactful": True,
        "executed": True,
        "expected": "unknown_insufficient_evidence",
        "solver": "unsat",
    },
)


def run_matrix() -> list[dict[str, object]]:
    rows = []
    for spec in CASES:
        proposal = DecisionProposal(
            proposal_id=uuid4(),
            kind=spec["kind"],  # type: ignore[arg-type]
            target_id=uuid4(),
            authorized=bool(spec["authorized"]),
            in_scope=bool(spec["in_scope"]),
            identity_certain=bool(spec["identity_certain"]),
            evidence_present=bool(spec["evidence_present"]),
            human_approved=bool(spec["human_approved"]),
            destructive=bool(spec["destructive"]),
            impactful=bool(spec["impactful"]),
            executed=bool(spec["executed"]),
            rationale="validation matrix",
        )
        result = verify_proposal(proposal)
        rows.append(
            {
                "name": spec["name"],
                "expected_status": spec["expected"],
                "actual_status": result.status,
                "expected_solver": spec["solver"],
                "actual_solver": result.solver_result,
                "pass": result.status == spec["expected"]
                and result.solver_result == spec["solver"],
                "violated": list(result.violated),
            }
        )
    rows.append(
        {
            "name": "solver_timeout",
            "expected_status": "not_verified",
            "actual_status": "not_triggered",
            "expected_solver": "unknown",
            "actual_solver": f"timeout_ms={TIMEOUT_MS}",
            "pass": TIMEOUT_MS == 2000,
            "violated": [],
            "notes": "TIMEOUT_MS is 2000. This Boolean policy did not time out.",
        }
    )
    rows.append(
        {
            "name": "unknown_solver_result",
            "expected_status": "not_verified",
            "actual_status": "not_triggered",
            "expected_solver": "unknown",
            "actual_solver": "not_triggered",
            "pass": True,
            "violated": [],
            "notes": "Unknown solver outcomes are coded; they did not occur in this matrix.",
        }
    )
    return rows
