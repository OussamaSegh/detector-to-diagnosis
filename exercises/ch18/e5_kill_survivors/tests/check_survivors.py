#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise 18.5: checks a mutation report of the sequence tracker against its review.

    check_survivors.py REPORT survivors.json --source FILE

REPORT is the output (--out) of tools/mutation_test.py. The check passes if the report is of FILE
as it is now (the report records its SHA-256), and survivors.json lists exactly the mutants that
survived, each with a reason of at least eight words why no test can kill it:

    {"equivalent": [{"mutant": "minidaq/include/minidaq/format/readout_packet.hpp:300:48 ror >= -> >",
                     "reason": "..."}]}
"""
import argparse
import hashlib
import json
import pathlib
import sys

MIN_REASON_WORDS = 8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report", type=pathlib.Path)
    ap.add_argument("review", type=pathlib.Path)
    ap.add_argument("--source", required=True, type=pathlib.Path)
    args = ap.parse_args()

    if not args.report.is_file():
        print(f"FAIL: no mutation report at {args.report}; run tools/mutation_test.py with --out (README.md)")
        return 1
    lines = args.report.read_text().splitlines()
    digest = hashlib.sha256(args.source.read_bytes()).hexdigest()
    problems = []
    if f"# source sha256 {digest}" not in lines:
        problems.append(f"the report is not of {args.source} as it is now; run tools/mutation_test.py again")
    survived = {line.split(None, 1)[1] for line in lines if line.startswith("survived ")}
    totals = [line for line in lines if line.startswith("# killed ")]
    if not totals:
        problems.append("the report has no totals: the run did not finish")
    listed = {}
    for e in json.loads(args.review.read_text()).get("equivalent", []):
        listed[e.get("mutant", "")] = str(e.get("reason", ""))
    for m in sorted(survived - listed.keys()):
        problems.append(f"survived, with no test and no reason: {m}")
    for m in sorted(listed.keys() - survived):
        problems.append(f"listed as equivalent but not a survivor in the report: {m}")
    for m in sorted(listed.keys() & survived):
        if len(listed[m].split()) < MIN_REASON_WORDS:
            problems.append(f"give a reason a reviewer can check: {m}")
    for p in problems:
        print("FAIL:", p)
    if problems:
        return 1
    print(f"ok: {totals[0][2:]}; {len(survived)} survivors, each argued equivalent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
