#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise 18.3: checks the branch coverage that one test executable reaches in one source file,
and the review of the branches it leaves.

    check_coverage.py --exe TESTS --source FILE --review review.json --min 90 --work DIR

Runs TESTS (a GoogleTest executable built with the coverage preset), measures the branches of FILE
with llvm-cov, and passes if the tests pass, the branch coverage of FILE is at least --min percent,
and review.json accepts, with a reason, exactly the branches still not taken both ways:

    {"accepted": [{"line": 110, "column": 11, "code": "switch (p.outcome) {",
                   "reason": "why no test can take this branch, or why none needs to"}]}

`code` is the line as it is in FILE, so an entry stops matching when the line changes.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4] / "tools"))
import coverage  # noqa: E402  (tools/coverage.py)

MIN_REASON_WORDS = 6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--source", required=True, type=pathlib.Path)
    ap.add_argument("--review", required=True, type=pathlib.Path)
    ap.add_argument("--min", type=float, default=90.0)
    ap.add_argument("--work", required=True, type=pathlib.Path)
    args = ap.parse_args()

    shutil.rmtree(args.work, ignore_errors=True)
    args.work.mkdir(parents=True)
    env = dict(os.environ, LLVM_PROFILE_FILE=str(args.work / "%p.profraw"))
    run = subprocess.run([args.exe], env=env, capture_output=True, text=True)
    if run.returncode != 0:
        print(run.stdout[-3000:])
        sys.exit("FAIL: the tests fail; coverage of failing tests is not evidence")
    profiles = sorted(str(p) for p in args.work.glob("*.profraw"))
    if not profiles:
        sys.exit("FAIL: no profile written; build with the coverage preset")
    merged = args.work / "merged.profdata"
    subprocess.run([coverage.tool("llvm-profdata"), "merge", "-sparse", *profiles, "-o", str(merged)], check=True)
    common = ["-instr-profile", str(merged), args.exe]
    export = json.loads(subprocess.run([coverage.tool("llvm-cov"), "export", "-summary-only", *common],
                                       check=True, capture_output=True, text=True).stdout)
    source = str(args.source.resolve())
    files = [f for f in export["data"][0]["files"] if f["filename"] == source]
    if not files:
        sys.exit(f"FAIL: {args.source} is not in the coverage data; do the tests call it?")
    b = files[0]["summary"]["branches"]
    percent = 100.0 * b["covered"] / b["count"] if b["count"] else 100.0
    shown = subprocess.run([coverage.tool("llvm-cov"), "show", "-show-branches=count", "-show-mcdc", *common,
                            source], check=True, capture_output=True, text=True).stdout
    lines, found = coverage.gaps(shown)
    open_gaps = {(ln, col) for ln, col, note in found if note.startswith("branch")}

    problems = []
    print(f"branch coverage of {args.source.name}: {percent:.1f}% ({b['covered']} of {b['count']})")
    if percent < args.min:
        problems.append(f"branch coverage {percent:.1f}% is below {args.min:g}%")
    accepted = json.loads(args.review.read_text()).get("accepted", [])
    reviewed = set()
    for e in accepted:
        key = (e.get("line"), e.get("column"))
        where = f"line {key[0]}, column {key[1]}"
        if key not in open_gaps:
            problems.append(f"review entry for {where}: no branch there is open; remove the entry")
        elif e.get("code", "").strip() != lines.get(key[0], ""):
            problems.append(f"review entry for {where}: the code is now `{lines.get(key[0], '')}`")
        elif len(str(e.get("reason", "")).split()) < MIN_REASON_WORDS:
            problems.append(f"review entry for {where}: give a reason a reviewer can check")
        else:
            reviewed.add(key)
    listed = {(e.get("line"), e.get("column")) for e in accepted}
    for ln, col, note in found:
        if note.startswith("branch") and (ln, col) not in listed:
            problems.append(f"line {ln}, column {col}: {note}, not reviewed: `{lines.get(ln, '')}`")
    for p in problems:
        print("FAIL:", p)
    if problems:
        sys.exit(1)
    print(f"ok: {len(reviewed)} open branches, each accepted with a reason")


if __name__ == "__main__":
    main()
