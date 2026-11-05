"""Phase 12 CLI.

Default: evaluate DMBD-like JSONL from SYNAPSE_DMBD_JSONL or fail closed.

  python -m synapse_validation.phase12
  python -m synapse_validation.phase12 --synthetic-protocol PATH
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from synapse_validation.phase12.report import write_outputs
from synapse_validation.phase12.run import ROOT, run_phase12


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 12 endpoint-evidence runner")
    parser.add_argument(
        "--synthetic-protocol",
        metavar="JSONL",
        help="Explicit synthetic protocol fixture. Never labelled as DMBD.",
    )
    args = parser.parse_args(argv)
    if args.synthetic_protocol:
        payload = run_phase12(mode="synthetic_protocol", jsonl_path=Path(args.synthetic_protocol))
        code = 0
    else:
        payload = run_phase12(mode="external")
        code = 0 if payload.get("dmbd_evaluated") else 2
    json_path, md_path = write_outputs(payload, ROOT)
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print(f"dmbd_evaluated={payload.get('dmbd_evaluated')}")
    if payload.get("blocker"):
        print(f"blocker={payload['blocker']}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
