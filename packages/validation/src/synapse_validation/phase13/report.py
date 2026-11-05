"""Write Phase 13 reports without touching Phase 10–12 generated files."""

from __future__ import annotations

import json
from pathlib import Path


def render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Phase 13 research results",
        "",
        "Status: **EXPERIMENTAL**. Phase 10–12 generated findings are preserved.",
        "",
        "## Scientific completion",
        "",
        f"**scientific_completion={payload.get('scientific_completion')}**",
        f"**independent_endpoint_validation_completed="
        f"{payload.get('independent_endpoint_validation_completed')}**",
        f"**dmbd_process_trees_evaluated={payload.get('dmbd_process_trees_evaluated')}**",
        f"**dmbd_labels_inspected={payload.get('dmbd_labels_inspected')}**",
        f"**winmet_evaluated={payload.get('winmet_evaluated')}**",
        f"**optc_evaluated={payload.get('optc_evaluated')}**",
        "",
    ]
    if not payload.get("evaluated"):
        lines.extend(
            [
                f"Blocker: {payload.get('blocker')}",
                "",
                "No independent process-tree metrics were produced.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                f"Dataset class: **{payload.get('dataset_class')}**.",
                "If this class is `synthetic_endpoint_protocol`, it is **not** DMBD.",
                "",
                "## Reconstruction (structural)",
                "",
                "```json",
                json.dumps(payload.get("reconstruction"), indent=2, default=str),
                "```",
                "",
                "## Sample-level detection",
                "",
                "```json",
                json.dumps(payload.get("detection"), indent=2, default=str)[:8000],
                "```",
                "",
            ]
        )
    labels = payload.get("dmbd_labels") or {}
    lines.extend(
        [
            "## DMBD label files (not process trees)",
            "",
            "```json",
            json.dumps(labels, indent=2, default=str)[:8000],
            "```",
            "",
            "## Preserved prior findings",
            "",
            json.dumps(payload.get("phase10_preserved"), indent=2),
            "",
            json.dumps(payload.get("phase11_preserved"), indent=2),
            "",
            json.dumps(payload.get("phase12_preserved"), indent=2),
            "",
            "## Limitations",
            "",
            "- Label JSON is not process reconstruction.",
            "- Sample AV labels are not event-level malice.",
            "- pid_hash is not Linux boot_id/start_ticks.",
            "- Z3 SAT is not real-world safety.",
            "- Completeness-aware abstention is not a calibrated probability.",
            "",
        ]
    )
    return "\n".join(str(item) for item in lines) + "\n"


def write_outputs(payload: dict[str, object], root: Path) -> dict[str, Path]:
    phase_dir = root / "docs" / "research" / "phase-13"
    generated = root / "docs" / "research" / "generated"
    phase_dir.mkdir(parents=True, exist_ok=True)
    generated.mkdir(parents=True, exist_ok=True)
    json_path = generated / "phase13-last-run.json"
    report_path = phase_dir / "phase-13-report.md"
    results_path = phase_dir / "phase-13-results.json"
    config_path = phase_dir / "phase-13-experiment-config.json"
    schema_path = phase_dir / "phase-13-schema-report.json"
    manifest_path = phase_dir / "phase-13-dataset-manifest.json"
    inspection_json = phase_dir / "dataset-inspection.json"
    inspection_md = phase_dir / "dataset-inspection.md"
    blob = json.dumps(payload, indent=2, default=str) + "\n"
    json_path.write_text(blob, encoding="utf-8")
    results_path.write_text(blob, encoding="utf-8")
    report_path.write_text(render_markdown(payload), encoding="utf-8")
    config_path.write_text(
        json.dumps(
            {
                "experiment_id": payload.get("experiment_id"),
                "feature_schema": payload.get("feature_schema"),
                "mode": payload.get("mode"),
                "acquisition_bound_bytes": payload.get("acquisition_bound_bytes"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    schema_path.write_text(
        json.dumps(
            {
                "feature_definitions": payload.get("feature_definitions"),
                "inspection": payload.get("inspection"),
                "dmbd_labels": payload.get("dmbd_labels"),
            },
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(payload.get("manifest"), indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    inspection_json.write_text(
        json.dumps(
            {
                "process_jsonl": payload.get("inspection"),
                "dmbd_labels": payload.get("dmbd_labels"),
                "completed": bool(payload.get("evaluated")),
            },
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    inspected = payload.get("evaluated")
    inspection_md.write_text(
        "# Dataset inspection\n\n"
        + (
            "Process JSONL was inspected.\n"
            if inspected
            else "Process JSONL inspection was **not** completed (dataset absent).\n"
        )
        + "\nLabel files are documented in `phase-13-schema-report.json`.\n",
        encoding="utf-8",
    )
    return {
        "last_run": json_path,
        "report": report_path,
        "results": results_path,
    }
