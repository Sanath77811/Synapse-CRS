# Explainability evaluation

Status: **IMPLEMENTED** on synthetic reconstructions. **NOT EVALUATED** on live production incidents.

## Metrics (documented, not subjective)

| Metric | Definition |
| --- | --- |
| Evidence reference validity | 1 if every cited event ID exists in the reconstruction observations |
| Evidence coverage | Cited observed IDs / observation IDs |
| Rule traceability | 1 if every explanation rule ID exists in `RULES` |
| Explanation completeness | Fraction of required narrative fields that are non-empty |
| Unsupported claim count | Selected-hypothesis event IDs not in observations, plus mismatched explanation IDs |
| Provenance consistency | Inferred timeline items have `event_id is None`; observed items have an id |

No Likert “explanation quality” score is used.

## Adversarial fixtures

Identity-gap reconstructions omit `process_started`. The timeline must keep inferred gaps without pretending they are stored events. Missing evidence remains listed. Contradictory complete-lifecycle-plus-volume scenarios retain both start/exit and Phase 8 volume findings.

## Claims

Explanations must match the structured assessment. Natural language is not the source of truth.
