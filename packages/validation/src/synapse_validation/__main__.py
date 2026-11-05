"""Run the research evaluation harness.

PYTHONPATH=... python -m synapse_validation
"""

from pathlib import Path

from synapse_validation.experiments import run_all
from synapse_validation.report import write_json, write_markdown

ROOT = Path(__file__).resolve().parents[4]


def main() -> None:
    payload = run_all()
    json_path = ROOT / "docs" / "research" / "generated" / "last-run.json"
    md_path = ROOT / "docs" / "research" / "benchmark-results.md"
    write_json(payload, json_path)
    write_markdown(payload, md_path)
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print(f"cicids_available={payload['cicids2017']['available']}")


if __name__ == "__main__":
    main()
