"""Z3 checks on encoded explanation policy. SAT is not real-world safety."""

from __future__ import annotations

from z3 import Bool, Implies, Not, Solver, sat, unknown, unsat

TIMEOUT_MS = 2000


def verify_claim_policy(
    *,
    insufficient_evidence: bool,
    claim_malicious: bool,
    has_source_records: bool,
) -> dict[str, object]:
    solver = Solver()
    solver.set("timeout", TIMEOUT_MS)
    insufficient = Bool("insufficient")
    claim = Bool("claim_malicious")
    records = Bool("has_source_records")
    solver.add(insufficient == insufficient_evidence)
    solver.add(claim == claim_malicious)
    solver.add(records == has_source_records)
    solver.add(Implies(claim, records))
    solver.add(Implies(insufficient, Not(claim)))
    status = solver.check()
    if status == sat:
        result = "sat"
    elif status == unsat:
        result = "unsat"
    elif status == unknown:
        result = "unknown"
    else:
        result = str(status)
    return {
        "result": result,
        "policy": (
            "claim_malicious implies has_source_records; insufficient_evidence implies not claim"
        ),
        "inputs": {
            "insufficient_evidence": insufficient_evidence,
            "claim_malicious": claim_malicious,
            "has_source_records": has_source_records,
        },
        "notes": "SAT means the encoded facts obey the policy model. It is not host safety.",
    }
