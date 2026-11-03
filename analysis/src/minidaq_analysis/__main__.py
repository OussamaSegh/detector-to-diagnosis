# SPDX-License-Identifier: MIT
"""minidaq-qc RUN.run.json OUT_DIR [--protocol FILE.toml]: the acquisition QC report of one run.

Exit status 0 if every check passes, 1 if one fails, 2 if the run cannot be analyzed (a damaged
file, a fit that does not converge)."""
from __future__ import annotations

import argparse
import pathlib
import sys

from .listmode import FormatError
from .report import write_report


def main(argv: list[str] | None = None) -> int:
    args_list = sys.argv[1:] if argv is None else argv
    p = argparse.ArgumentParser(prog="minidaq-qc", description=__doc__.splitlines()[0])
    p.add_argument("record", type=pathlib.Path, help="the run record, <prefix>-<run>.run.json")
    p.add_argument("out", type=pathlib.Path, help="directory for the report")
    p.add_argument("--protocol", type=pathlib.Path, help="QC protocol (TOML); default: built in")
    a = p.parse_args(args_list)
    try:
        report = write_report(a.record, a.out, a.protocol, ["minidaq-qc", *args_list])
    except (FormatError, RuntimeError, ValueError, OSError, KeyError) as e:
        print(f"minidaq-qc: {e}", file=sys.stderr)
        return 2
    for c in report["checks"]:
        print(f"{'pass' if c['passed'] else 'FAIL'}  {c['name']}: {c['value']:.6g}"
              + (f" ± {c['error']:.2g}" if c["error"] is not None else ""))
    print("PASS" if report["passed"] else "FAIL")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
