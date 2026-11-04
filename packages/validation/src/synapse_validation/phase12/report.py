"""Human-readable Phase 12 report. Does not overwrite Phase 10/11 results."""

from __future__ import annotations

import json
from pathlib import Path


def render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Phase 12 research results",
        "",
        "Status: **EXPERIMENTAL**. Phase 10 and Phase 11 findings are preserved.",
        "",
        "## Independent endpoint validation",
        "",
        f"**dmbd_evaluated={payload.get('dmbd_evaluated')}**",
        f"**winmet_evaluated={payload.get('winmet_evaluated')}**",
        f"**optc_evaluated={payload.get('optc_evaluated')}**",
        f"**independent_endpoint_validation_completed="
        f"{payload.get('independent_endpoint_validation_completed')}**",
        "",
    ]
    if not payload.get("evaluated"):
        lines.extend(
            [
                f"Blocker: {payload.get('blocker')}",
                "",
                "No independent endpoint benchmark metrics were produced.",
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
                json.dumps(payload.get("reconstruction"), indent=2),
                "",
                "## Sample-level detection",
                "",
                json.dumps(payload.get("detection"), indent=2)[:5000],
                "",
            ]
        )
    lines.extend(
        [
            "## Suitability matrix",
            "",
            json.dumps(payload.get("suitability_matrix"), indent=2),
            "",
            "## Preserved prior findings",
            "",
            json.dumps(payload.get("phase10_preserved"), indent=2),
            "",
            json.dumps(payload.get("phase11_preserved"), indent=2),
            "",
            "## Limitations",
            "",
            "- Do not treat sample AV labels as event-level malice.",
            "- Do not map pid_hash onto Linux boot_id/start_ticks.",
            "- SAT/Z3 remains a policy-model result, not real-world safety.",
            "",
        ]
    )
    return "\n".join(str(item) for item in lines) + "\n"


def write_outputs(payload: dict[str, object], root: Path) -> tuple[Path, Path]:
    json_path = root / "docs" / "research" / "generated" / "phase12-last-run.json"
    md_path = root / "docs" / "research" / "phase-12-results.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return json_path, md_path
