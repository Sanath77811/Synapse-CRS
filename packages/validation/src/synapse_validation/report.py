"""JSON and Markdown reports from measured experiment output."""

from __future__ import annotations

import json
from pathlib import Path


def write_json(payload: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def _exp(payload: dict, experiment_id: str) -> dict:
    for item in payload["experiments"]:
        if item["experiment_id"] == experiment_id:
            return item
    raise KeyError(experiment_id)


def render_markdown(payload: dict[str, object]) -> str:
    a = _exp(payload, "A_deterministic_correlation")
    b = _exp(payload, "B_neural_only")
    c = _exp(payload, "C_symbolic_only")
    d = _exp(payload, "D_hybrid")
    e1 = _exp(payload, "E_neural_plus_symbolic")
    e2 = _exp(payload, "E_hybrid_without_evidence_quality")
    cic = payload["cicids2017"]
    pred = payload["prediction"]
    explain = payload["explainability"]
    lines = [
        "# Research benchmark results",
        "",
        "Status: **EXPERIMENTAL**. Every number below was generated from",
        f"`{payload['experiment_id']}` (`validation_version` {payload['validation_version']}).",
        "Synthetic-lab metrics are not enterprise detection performance.",
        "",
        "## 1. Executive summary",
        "",
        "Hybrid neuro-symbolic reasoning was compared with Phase 8 correlation,",
        "Isolation Forest scoring, and symbolic rules on twelve constructed",
        "synthetic reconstructions (four typical, four unusual-volume, four",
        "identity-gap). CIC-IDS2017 was **not present** in this environment unless",
        "an operator supplied `SYNAPSE_CICIDS_CSV`.",
        "",
        f"- Correlation 3-class accuracy: **{a['multiclass_accuracy']}** (synthetic).",
        f"- Neural-only 3-class accuracy: **{b['multiclass_accuracy']}** (synthetic).",
        "  Neural-only cannot emit the insufficient class.",
        f"- Symbolic-only 3-class accuracy: **{c['multiclass_accuracy']}** (synthetic).",
        f"- Hybrid 3-class accuracy: **{d['multiclass_accuracy']}** (synthetic).",
        f"- Persistence advantage: **{pred['measurable_advantage_over_persistence']}**.",
        f"- CIC-IDS2017 available: **{cic['available']}**.",
        "",
        "## 2. Research objectives",
        "",
        "Primary: measure whether hybrid reasoning helps, hurts, or matches",
        "standalone components on documented tasks. Secondary: traceability,",
        "explanation faithfulness, unusual vs malicious distinction, forecast",
        "baselines, counterfactual consistency, Z3 policy, and cost.",
        "",
        "## 3. Architecture under evaluation",
        "",
        f"Engine `{payload['engine_version']}`.",
        f"Feature schema `{payload['feature_schema_version']}`.",
        f"Model `{payload['model_version']}`. Rules `{payload['rule_version']}`.",
        "",
        "## 4. Dataset description",
        "",
        f"Name `{payload['dataset_name']}` version `{payload['dataset_version']}`.",
        f"Size {payload['dataset_size_scenarios']} reconstructions.",
        f"Labels: `{payload['label_counts']}`.",
        "Class: **synthetic_lab**.",
        "",
        "## 5. Dataset limitations",
        "",
        "- Fixtures are constructed, not captured from production hosts.",
        "- Labels describe lab construction (typical / volume / gap), not attacker intent.",
        "- CIC-IDS2017 is a flow dataset and is not mapped onto process identities.",
        "",
        "## 6. Feature compatibility",
        "",
        f"CIC-IDS adapter available: {cic['available']}.",
        f"Compatibility counts: `{cic['compatibility']}`.",
        "Zero Synapse `synthetic_lab_features_v1` fields are directly compatible with CIC-IDS2017.",
        "",
        "## 7. Experimental methodology",
        "",
        "Fixed seed 42. Sequential group-or-sequential split recorded; A–E report the",
        "full fixture set because no classifier is fitted on these reconstructions.",
        "Neural thresholds were not tuned on this fixture set.",
        f"Split notes: {payload['split']['notes']}",
        "",
        "## 8. Baseline results",
        "",
        _metrics_block(a),
        "",
        "## 9. Neural-only results",
        "",
        _metrics_block(b),
        "",
        f"Synthetic feature holdout F1="
        f"{payload['neural_holdout_synthetic_features']['f1']} "
        f"(precision={payload['neural_holdout_synthetic_features']['precision']}, "
        f"recall={payload['neural_holdout_synthetic_features']['recall']}, "
        f"FPR={payload['neural_holdout_synthetic_features']['false_positive_rate']}). "
        "PR-AUC/ROC-AUC: not reported on this tiny holdout.",
        "",
        "## 10. Symbolic-only results",
        "",
        _metrics_block(c),
        "",
        "## 11. Hybrid results",
        "",
        _metrics_block(d),
        "",
        "## 12. Ablation results",
        "",
        _metrics_block(e1),
        "",
        _metrics_block(e2),
        "",
        "## 13. Prediction results",
        "",
        f"Persistence MAE={pred['persistence_mae']}.",
        f"Historical-mean MAE={pred['historical_mean_mae']}.",
        f"Shipped model equals persistence: {pred['model_equals_persistence']}.",
        f"Measurable advantage: {pred['measurable_advantage_over_persistence']}.",
        "Measured on synthetic chronological counts. Not a labelled attack forecast.",
        "",
        "## 14. Explainability validation",
        "",
        f"Mean evidence coverage={explain['mean_evidence_coverage']}.",
        f"All evidence references valid={explain['all_reference_valid']}.",
        f"All rule IDs traceable={explain['all_rules_traceable']}.",
        f"Unsupported claim total={explain['unsupported_claim_total']}.",
        "",
        "## 15. Counterfactual validation",
        "",
        json.dumps(payload["counterfactuals"], indent=2),
        "",
        "## 16. Formal verification validation",
        "",
        json.dumps(payload["formal_verification"], indent=2),
        "",
        "SAT under the encoded policy is not a proof of real-world safety.",
        "No proposal is executed.",
        "",
        "## 17. Performance analysis",
        "",
        json.dumps(payload["performance"], indent=2),
        "",
        f"Software: {payload['software']}",
        "",
        "## 18. Threats to validity",
        "",
        "- Constructed labels can leak the same rules used for detection.",
        "- Twelve scenarios cannot support generalization claims.",
        "- Neural-only three-class accuracy is penalized because it cannot emit `insufficient`.",
        "- CIC-IDS2017, if supplied, remains a different feature space.",
        "",
        "## 19. Limitations",
        "",
        *[f"- {item}" for item in payload["known_limitations"]],
        "",
        "## 20. Conclusions",
        "",
        _conclusions(a, b, c, d),
        "",
        "## 21. Future research",
        "",
        "- Operator-supplied CIC-IDS2017 adapter runs (flow-level, labelled as such).",
        "- Larger independently labelled process-level corpora.",
        "- Quantified forecast uncertainty if a non-persistence model is introduced.",
        "",
    ]
    return "\n".join(lines) + "\n"


def _metrics_block(item: dict) -> str:
    binary = item["unusual_volume_binary"]
    return (
        f"**{item['experiment_id']}** ({item['dataset_class']}). Task: {item['task']}.\n\n"
        f"Three-class accuracy={item['multiclass_accuracy']}. "
        f"Unusual-volume precision={binary['precision']} recall={binary['recall']} "
        f"F1={binary['f1']} FPR={binary['false_positive_rate']} "
        f"TP={binary['true_positive']} FP={binary['false_positive']} "
        f"TN={binary['true_negative']} FN={binary['false_negative']}. "
        f"Elapsed={item['elapsed_seconds']}s."
    )


def _conclusions(a, b, c, d) -> str:
    hybrid = d["multiclass_accuracy"]
    best_standalone = max(
        a["multiclass_accuracy"], b["multiclass_accuracy"], c["multiclass_accuracy"]
    )
    if hybrid > best_standalone:
        relation = "higher than"
    elif hybrid < best_standalone:
        relation = "lower than"
    else:
        relation = "equal to"
    return (
        f"On this synthetic twelve-scenario fixture, hybrid three-class accuracy "
        f"({hybrid}) is {relation} the best standalone component "
        f"({best_standalone}). This is not a claim about enterprise detection. "
        "Hybrid value on this set is inspected per class in the JSON metrics, "
        "especially identity-gap handling versus neural-only."
    )


def write_markdown(payload: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(payload), encoding="utf-8")
