"""Phase 13 CLI.

Default: fail closed unless SYNAPSE_DMBD_JSONL process evidence exists.

  python -m synapse_validation.phase13
  python -m synapse_validation.phase13 --synthetic-protocol PATH
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from synapse_validation.phase13.report import write_outputs
from synapse_validation.phase13.run import ROOT, run_phase13


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 13 independent-evidence runner")
    parser.add_argument(
        "--synthetic-protocol",
        metavar="JSONL",
        help="Explicit synthetic protocol fixture. Never labelled as DMBD.",
    )
    args = parser.parse_args(argv)
    if args.synthetic_protocol:
        payload = run_phase13(
            mode="synthetic_protocol",
            jsonl_path=Path(args.synthetic_protocol),
        )
        code = 0
    else:
        payload = run_phase13(mode="external")
        code = 0 if payload.get("independent_endpoint_validation_completed") else 2
    paths = write_outputs(payload, ROOT)
    print(f"wrote {paths['last_run']}")
    print(f"wrote {paths['report']}")
    print(f"scientific_completion={payload.get('scientific_completion')}")
    if payload.get("blocker"):
        print(f"blocker={payload['blocker']}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
