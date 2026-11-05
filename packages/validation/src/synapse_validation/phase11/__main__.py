"""Phase 11 CLI.

Default: evaluate CIC-IDS2017 from SYNAPSE_CICIDS_CSV or fail closed.

  python -m synapse_validation.phase11
  python -m synapse_validation.phase11 --synthetic-protocol PATH
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from synapse_validation.phase11.report import write_outputs
from synapse_validation.phase11.run import ROOT, run_phase11


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 11 flow-benchmark runner")
    parser.add_argument(
        "--synthetic-protocol",
        metavar="CSV",
        help="Explicit synthetic protocol fixture. Never labelled as CIC-IDS2017.",
    )
    args = parser.parse_args(argv)
    if args.synthetic_protocol:
        payload = run_phase11(mode="synthetic_protocol", csv_path=Path(args.synthetic_protocol))
        code = 0
    else:
        payload = run_phase11(mode="external")
        code = 0 if payload.get("cicids2017_evaluated") else 2
    json_path, md_path = write_outputs(payload, ROOT)
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print(f"cicids2017_evaluated={payload.get('cicids2017_evaluated')}")
    if payload.get("blocker"):
        print(f"blocker={payload['blocker']}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
