# Phase 11 methodology

Status: **IMPLEMENTED** as a separate flow-benchmark track. CIC-IDS2017 scoring: **NOT EVALUATED** unless operator-supplied files exist and `make research-eval-phase11` reports `cicids2017_evaluated=True`.

Phase 10 synthetic reconstruction results remain the record for endpoint hybrid comparison. This phase does not overwrite them.

## Research questions

- RQ1: How well do suitable baselines detect malicious **network-flow** records on an independent dataset?
- RQ2: Does a hybrid method help when all methods have equivalent eligible inputs?
- RQ3: Are explanations grounded in actual flow records?
- RQ4: Robustness to missing fields, noise, imbalance, unseen labels.
- RQ5: Which Synapse-CRS capabilities cannot be validated from flows?

RQ2's Phase 9 hybrid answer on CIC-IDS2017 is **not comparable**. A flow-level union of Isolation Forest and a volume rule is a **new ensemble**, not engine 0.6.0.

## Evidence domains

| Domain | What it is | What it is not |
| --- | --- | --- |
| A External flows | CIC-IDS2017 CSV if present | Enrolled Linux telemetry |
| B Linux agent | Existing Phase 8–9 pipeline | Not re-benchmarked here |
| C Synthetic fixtures | Protocol tests and Phase 10 reconstructions | CIC-IDS2017 |

## Split and leakage

Prefer Timestamp order, else sequential file order. Seed 42. Medians and the volume percentile are fit on **train**. Isolation Forest threshold uses **validation F1** when both classes exist. Test labels are never used for fitting. Identifier fields (Flow ID, IPs, Source Port, Timestamp as a feature) are excluded. Duplicate signatures across splits are counted, not silently dropped.

## Models

| ID | Task | Notes |
| --- | --- | --- |
| majority | Binary flow | Training majority class |
| volume_rule | Binary flow | Train-benign 95th percentile of packet totals |
| isolation_forest | Binary flow | Fit on train BENIGN; score is not a probability |
| flow_union | Binary flow | Rule OR forest; **not** Phase 9 hybrid |
| phase9_hybrid | n/a | **not comparable** on flows |

## Metrics

Binary malicious = not BENIGN. Report confusion counts, precision, recall, F1, FPR, FNR, accuracy, balanced accuracy, macro/weighted F1, per-class scores, PR-AUC and ROC-AUC when both classes exist, and a percentile bootstrap of F1 (descriptive, not a p-value).

## Commands

External (fails closed if the corpus is missing):

```bash
make research-eval-phase11
```

Explicit synthetic protocol (never labelled CIC-IDS2017):

```bash
python -m synapse_validation.phase11 --synthetic-protocol tests/fixtures/validation/synthetic_flow_protocol.csv
```
