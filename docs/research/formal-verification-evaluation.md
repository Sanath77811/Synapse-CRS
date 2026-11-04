# Formal verification evaluation

Status: Z3 policy checks **IMPLEMENTED**. Runtime execution of proposals: **NOT IMPLEMENTED** (forbidden).

## Encoded constraints (policy 1.0.0)

`executed_is_false`, `destructive_is_false`, `authorized`, `in_scope`, `identity_certain`, `evidence_present`, `human_approval_if_impactful`, `mitigation_kind_forbidden`.

Solver: Z3, timeout 2000 ms.

## Matrix

Authorized investigation → SAT `verified_under_model`.

Unauthorized, out of scope, unknown identity, missing evidence, missing approval on an impactful isolate recommendation, destructive mitigation, forbidden `execute_host_mitigation`, executed=true → UNSAT / rejected or `unknown_insufficient_evidence`.

Timeout and unknown solver results are coded. This Boolean policy did not time out in the recorded run.

## SAT is not safety

Satisfiability means the encoded Boolean assignment meets the encoded constraints. It does not prove a host is safe, that evidence is complete, or that a recommendation should be followed. No proposal executes.
