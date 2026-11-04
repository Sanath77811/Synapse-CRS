# Hybrid neuro-symbolic reasoning foundation

Status: **IMPLEMENTED** as a research foundation (engine 0.6.0). Not a complete autonomous cyber reasoning system.

## Data flow

Verified enrolled telemetry → Phase 8 correlation → reconstruction → versioned features → Isolation Forest (synthetic baseline) + symbolic rules → competing hypotheses → explanation → optional volume forecast → feature-ablation counterfactual → Z3-checked recommendation (never executed).

Epistemic classes stay separate: observed, correlated, inferred.

## Neural model

Isolation Forest (`isolation-forest-synthetic-baseline-v1`) fitted in-process from `packages/reasoning/src/synapse_reasoning/data/baseline_features_v1.json` (30 typical synthetic rows, seed 42). No pickle. `unusualness_score = -decision_function` is a score, not a probability. Training data is synthetic lab behaviour, not CIC-IDS or enterprise traffic.

## Symbolic rules

Inspectable table in `symbolic.py` (`RULE_VERSION` 1.0.0). Rules name required evidence, conditions, hypothesis, support, and limitations.

## Hypotheses

H1 normal, H2 unusual legitimate, H3 suspicious pattern, H4 insufficient evidence. Ties prefer H4 then H1 over H3.

## Implemented / experimental / not implemented

| Capability | Status |
|---|---|
| Reconstruction, timeline, process identity, graph | Implemented and tested |
| Isolation Forest baseline | Implemented; evaluated only on tiny synthetic holdout |
| Symbolic rules + hybrid orchestration | Implemented and tested |
| Structured explanations | Implemented and tested |
| Event-volume persistence forecast | Experimental |
| Feature-ablation counterfactuals | Implemented; not causal identification |
| Z3 policy verification of recommendations | Implemented and tested |
| Runtime mitigation / hotpatch | Not implemented (proposals only) |
| LLM explanations | Not implemented |
| CIC-IDS or other public IDS datasets | Adapter implemented; dataset not bundled; features not comparable to process telemetry |
| Research experiments A–E | Implemented on synthetic labelled reconstructions |
| Enterprise / CIC-IDS detection rates | Not evaluated unless operator CSV present (Phase 11) |
| Phase 11 flow-benchmark track | Implemented; fails closed without CIC-IDS2017 |
| Phase 9 hybrid on CIC-IDS2017 flows | Not comparable |
| Phase 12 endpoint adapter | Implemented; DMBD/WinMET/OpTC not evaluated in this checkout |
| Phase 9 hybrid on DMBD pid_hash | Not comparable |
| Phase 13 independent-evidence track | Implemented; process trees not acquired; label JSON is not tree evaluation |
| Completeness-aware sample method | Experimental; synthetic protocol only unless operator JSONL is supplied |
