# SPDX-License-Identifier: MIT
"""minidaq-qc RUN.run.json OUT_DIR [--protocol FILE.toml]: the acquisition QC report of one run.

With --keys DIR (release 1.3.0), the run must be signed by the server with a key in DIR and every
file must match its signed record, or no report is made. With --sign KEY, the report's files are
signed (``<file>.sig``).

Exit status 0 if every check passes, 1 if one fails, 2 if the run cannot be analyzed (a damaged
file, a fit that does not converge, a run whose signature does not verify)."""
from __future__ import annotations

import argparse
import pathlib
import sys

from .listmode import FormatError
from .report import write_report
from .signature import SignatureError, sign_report, verify_run


def main(argv: list[str] | None = None) -> int:
    args_list = sys.argv[1:] if argv is None else argv
    p = argparse.ArgumentParser(prog="minidaq-qc", description=__doc__.splitlines()[0])
    p.add_argument("record", type=pathlib.Path, help="the run record, <prefix>-<run>.run.json")
    p.add_argument("out", type=pathlib.Path, help="directory for the report")
    p.add_argument("--protocol", type=pathlib.Path, help="QC protocol (TOML); default: built in")
    p.add_argument("--keys", type=pathlib.Path,
                   help="directory of the public keys (*.pem) that may sign runs; refuse others")
    p.add_argument("--sign", type=pathlib.Path, help="Ed25519 private key that signs the report")
    a = p.parse_args(args_list)
    try:
        if a.keys is not None:
            key = verify_run(a.record, a.keys)
            print(f"run signed by {key}, every file unchanged")
        report = write_report(a.record, a.out, a.protocol, ["minidaq-qc", *args_list])
        if a.sign is not None:
            sign_report(a.out, a.sign)
    except SignatureError as e:
        print(f"minidaq-qc: not verified: {e}", file=sys.stderr)
        return 2
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
