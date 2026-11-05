# Formal decision verification

Z3 encodes policy 1.0.0:

- `executed` is false
- `destructive` is false
- authorized, in_scope, identity_certain, evidence_present
- impactful proposals require human_approved
- `execute_host_mitigation` is forbidden

SAT means the **encoded model** is satisfiable, not that a host is safe. UNSAT is a policy rejection. Unknown is a solver timeout.

Recommendations are records. Nothing is executed.
