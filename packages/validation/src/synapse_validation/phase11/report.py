"""Human-readable Phase 11 report. Does not overwrite Phase 10 results."""

from __future__ import annotations

import json
from pathlib import Path


def render_markdown(payload: dict[str, object]) -> str:
    cic = payload.get("cicids2017_evaluated")
    lines = [
        "# Phase 11 research results",
        "",
        "Status: **EXPERIMENTAL**. Phase 10 synthetic findings are preserved and are",
        "not reinterpreted here.",
        "",
        "## 1. Objectives and research questions",
        "",
        "RQ1 flow detection on an independent dataset; RQ2 hybrid benefit given",
        "equivalent inputs; RQ3 traceable explanations; RQ4 robustness; RQ5 what",
        "network flows cannot validate.",
        "",
        "## 2. CIC-IDS2017 evaluation status",
        "",
        f"**cicids2017_evaluated={cic}**",
        "",
    ]
    if not payload.get("evaluated"):
        lines.extend(
            [
                f"Blocker: {payload.get('blocker')}",
                "",
                "No CIC-IDS2017 metrics were produced. Synthetic protocol fixtures",
                "were not substituted for the missing corpus.",
                "",
            ]
        )
    else:
        dataset_class = payload.get("dataset_class")
        lines.extend(
            [
                f"Dataset class: **{dataset_class}**.",
                "If this class is `synthetic_flow_protocol`, these numbers are **not**",
                "CIC-IDS2017 results.",
                "",
                "## 3. Manifest summary",
                "",
                "```json",
                json.dumps(payload.get("manifest"), indent=2)[:4000],
                "```",
                "",
                "## 4. Split",
                "",
                "```json",
                json.dumps(payload.get("split"), indent=2)[:3000],
                "```",
                "",
                "## 5. Model results",
                "",
            ]
        )
        for model in payload.get("models", []):
            lines.append(f"### {model.get('model_id')}")
            if model.get("status") == "not_comparable":
                lines.append(f"Status: **not comparable**. {model.get('reason')}")
            else:
                binary = model.get("binary", {})
                lines.append(
                    f"F1={binary.get('f1')} precision={binary.get('precision')} "
                    f"recall={binary.get('recall')} FPR={binary.get('false_positive_rate')} "
                    f"balanced_accuracy={model.get('balanced_accuracy')} "
                    f"macro_f1={model.get('macro_f1')} PR-AUC={binary.get('pr_auc')} "
                    f"ROC-AUC={binary.get('roc_auc')}."
                )
                lines.append(f"Bootstrap F1: {binary.get('bootstrap')}.")
            lines.append("")
    lines.extend(
        [
            "## 6. Phase 10 findings (preserved)",
            "",
            "```json",
            json.dumps(payload.get("phase10_preserved_findings"), indent=2)[:2500],
            "```",
            "",
            "## 7. Capability matrix",
            "",
            json.dumps(payload.get("capability_matrix"), indent=2),
            "",
            "## 8. Negative findings",
            "",
            "- Phase 9 hybrid is not comparable on flow records.",
            "- Phase 10 already showed Isolation Forest failing unusual-volume reconstructions.",
            "- Absence of CIC-IDS2017 is reported as not evaluated, not as a zero score.",
            "",
            "## 9. Threats to validity",
            "",
            "- Bounded samples are not the full CIC week.",
            "- Rules and forests share the same four numeric fields.",
            "- Temporal splits still share capture artifacts if IPs were used (they are excluded).",
            "",
            "## 10. Limitations and future work",
            "",
            *[f"- {item}" for item in payload.get("limitations", [])],
            "- Independent process-level labelled corpora remain the next evidence need.",
            "",
        ]
    )
    if payload.get("evaluated"):
        lines.extend(
            [
                "## 11. Explanations and robustness",
                "",
                f"Explanations: {payload.get('explanations')}",
                "",
                f"Robustness: {payload.get('robustness')}",
                "",
                f"Performance: {payload.get('performance')}",
                "",
            ]
        )
    return "\n".join(str(item) for item in lines) + "\n"


def write_outputs(payload: dict[str, object], root: Path) -> tuple[Path, Path]:
    json_path = root / "docs" / "research" / "generated" / "phase11-last-run.json"
    md_path = root / "docs" / "research" / "phase-11-results.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return json_path, md_path
