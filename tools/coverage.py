#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Measures the test coverage of MiniDAQ's shipped code, per software item (Chapter 18).

Runs the unit and system tests (ctest labels "unit" and "system", Chapter 19) of a build made with
the `coverage` preset (Clang source-based coverage with MC/DC), merges the profiles of every
process the tests started (the system tests start the programs themselves), and
reports line, branch, MC/DC and function coverage for the files of each software item in
docs/architecture/software-items.json. Test code, exercises, fuzz targets and benchmarks are not
counted: the question is how much of the code that ships the tests exercise.

    cmake --preset coverage && cmake --build --preset coverage
    tools/coverage.py build/coverage OUT [--html] [--uncovered FILE]

Writes OUT/summary.txt (the table), OUT/summary.json, OUT/report.txt (llvm-cov's per-file report),
and with --html an annotated source tree in OUT/html. The raw and merged profiles stay in BUILD
(coverage-profiles/, coverage.profdata): they are large and can be made again. --uncovered FILE
prints every line of FILE with a branch or an MC/DC condition that the tests did not take both
ways. A shipped item whose program no test runs has no profile at all; the table lists it as "not
run by any test" rather than leaving it out.

Coverage says which code ran, not that it was checked: a test without an assertion covers as much
as one with. Read the numbers with Chapter 18's section on what coverage proves.
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

IGNORE = r"(\.deps|/tests/|/exercises/|/fuzz/|/benchmarks/|/build/)"
LLVM_SUFFIX = os.environ.get("LLVM_SUFFIX", "-18")


def tool(name):
    for candidate in (f"{name}{LLVM_SUFFIX}", name):
        if shutil.which(candidate):
            return candidate
    sys.exit(f"coverage: {name} not found (set LLVM_SUFFIX)")


def objects(build):
    """Every executable the build made from MiniDAQ's sources (tests and apps)."""
    found = []
    for p in sorted((build / "minidaq").rglob("*")):
        if p.is_file() and os.access(p, os.X_OK) and "CMakeFiles" not in p.parts and p.suffix == "":
            with p.open("rb") as f:
                if f.read(4) == b"\x7fELF":
                    found.append(p)
    return found


def percent(covered, count):
    return 100.0 * covered / count if count else None


def item_of(path, items):
    best = None
    for it in items:
        for prefix in it["paths"]:
            if path.startswith(prefix) and (best is None or len(prefix) > len(best[1])):
                best = (it, prefix)
    return best[0] if best else None


# [snippet:summary]
def summarize(export, root, items):
    """{item id: {metric: [covered, count]}} from llvm-cov's JSON export."""
    metrics = ("lines", "branches", "mcdc", "functions")
    rows = {}
    for f in export["data"][0]["files"]:
        rel = os.path.relpath(f["filename"], root)
        it = item_of(rel, items)
        if it is None:
            continue
        row = rows.setdefault(it["id"], {m: [0, 0] for m in metrics})
        for m in metrics:
            s = f["summary"].get(m, {"covered": 0, "count": 0})
            row[m][0] += s["covered"]
            row[m][1] += s["count"]
    return rows
# [/snippet:summary]


def table(rows, items):
    def cell(pair):
        p = percent(*pair)
        return f"{p:5.1f}% {pair[0]:>5}/{pair[1]:<5}" if p is not None else f"{'-':>6} {'':>11}"

    header = f"{'item':<10} {'class':<5} {'lines':<18} {'branches':<18} {'MC/DC conditions':<18} functions"
    out = [header, "-" * len(header)]
    total = {m: [0, 0] for m in ("lines", "branches", "mcdc", "functions")}
    for it in items:
        if it["id"] not in rows:
            # No profile holds any of its code: no test ran the program it is in. Leaving the
            # row out would hide the largest gap of all.
            if it.get("shipped"):
                out.append(f"{it['id']:<10} {it.get('class') or '-':<5} not run by any test")
            continue
        r = rows[it["id"]]
        for m in total:
            total[m][0] += r[m][0]
            total[m][1] += r[m][1]
        out.append(f"{it['id']:<10} {it.get('class') or '-':<5} {cell(r['lines'])} {cell(r['branches'])} "
                   f"{cell(r['mcdc'])} {cell(r['functions'])}")
    out.append("-" * len(header))
    out.append(f"{'all':<10} {'':<5} {cell(total['lines'])} {cell(total['branches'])} {cell(total['mcdc'])} "
               f"{cell(total['functions'])}")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("build", type=pathlib.Path)
    ap.add_argument("out", type=pathlib.Path)
    ap.add_argument("--html", action="store_true")
    ap.add_argument("--uncovered", metavar="FILE", help="list the lines of FILE with a branch not taken both ways")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--no-run", action="store_true", help="reuse the profiles of an earlier run in BUILD")
    args = ap.parse_args()
    root = pathlib.Path(__file__).resolve().parent.parent
    build = args.build.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    profiles = build / "coverage-profiles"  # hundreds of MB: kept in the build, not with the report
    items = json.loads((root / "docs/architecture/software-items.json").read_text())["items"]

    if not args.no_run:
        shutil.rmtree(profiles, ignore_errors=True)
        profiles.mkdir(parents=True)
        env = dict(os.environ, LLVM_PROFILE_FILE=str(profiles / "%p-%m.profraw"))
        tests = subprocess.run(["ctest", "--test-dir", str(build), "-L", "unit|system", "-j", str(args.jobs),
                                "--output-on-failure"], env=env, capture_output=True, text=True)
        (out / "ctest.txt").write_text(tests.stdout + tests.stderr)
        if tests.returncode != 0:
            print(tests.stdout[-3000:], file=sys.stderr)
            sys.exit("coverage: the tests failed; coverage of a failing suite is not evidence")
    raw = sorted(profiles.glob("*.profraw"))
    if not raw:
        sys.exit(f"coverage: no profiles in {profiles}; was the build made with the coverage preset?")
    merged = build / "coverage.profdata"
    subprocess.run([tool("llvm-profdata"), "merge", "-sparse", "-o", str(merged), *map(str, raw)], check=True)

    objs = objects(build)
    obj_args = [str(objs[0])] + [a for o in objs[1:] for a in ("-object", str(o))]
    common = ["-instr-profile", str(merged), f"-ignore-filename-regex={IGNORE}"]
    export = subprocess.run([tool("llvm-cov"), "export", "-summary-only", *common, *obj_args],
                            check=True, capture_output=True, text=True).stdout
    report = subprocess.run([tool("llvm-cov"), "report", "-show-mcdc-summary", *common, *obj_args],
                            check=True, capture_output=True, text=True).stdout
    (out / "report.txt").write_text(report)
    rows = summarize(json.loads(export), root, items)
    text = table(rows, items)
    (out / "summary.txt").write_text(text)
    (out / "summary.json").write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n")
    print(text, end="")
    print(f"{len(raw)} profiles from {len(objs)} executables; report in {out}")

    if args.html:
        subprocess.run([tool("llvm-cov"), "show", "-format=html", "-show-branches=count", "-show-mcdc",
                        f"-output-dir={out / 'html'}", *common, *obj_args], check=True)
    if args.uncovered:
        source = (root / args.uncovered).resolve()
        if not source.is_file():  # llvm-cov would silently show every file instead
            sys.exit(f"coverage: no such source file {args.uncovered}")
        source = str(source)
        shown = subprocess.run([tool("llvm-cov"), "show", "-show-branches=count", "-show-mcdc", *common,
                                *obj_args, source], check=True, capture_output=True, text=True).stdout
        print(uncovered(shown))


# [snippet:uncovered]
BRANCH = re.compile(r"Branch \((\d+):(\d+)\): \[True: ([^,]+), False: ([^\]]+)\]")
DECISION = re.compile(r"MC/DC Decision Region \((\d+):(\d+)\)")
CONDITION = re.compile(r"Condition C(\d+) --> \((\d+):(\d+)\)")
PAIR = re.compile(r"C(\d+)-Pair: (covered|not covered)")


def gaps(shown):
    """({line: source}, [(line, column, note)]) from `llvm-cov show` output: each branch not taken
    both ways, and each MC/DC condition never shown to decide its decision alone. A template or an
    inline function appears once per instantiation; a branch counts as taken if any instantiation
    took it."""
    source, taken, conditions, covered = {}, {}, {}, {}
    decision = None
    for line in shown.splitlines():
        cells = line.split("|", 2)
        if len(cells) == 3 and cells[0].strip().isdigit():
            source[int(cells[0])] = cells[2].strip()
        elif m := BRANCH.search(line):
            key = (int(m[1]), int(m[2]))
            was = taken.get(key, (False, False))
            taken[key] = (was[0] or m[3].strip() != "0", was[1] or m[4].strip() != "0")
        elif m := DECISION.search(line):
            decision = (int(m[1]), int(m[2]))
        elif (m := CONDITION.search(line)) and decision:
            conditions[(decision, int(m[1]))] = (int(m[2]), int(m[3]))
        elif (m := PAIR.search(line)) and decision:
            key = (decision, int(m[1]))
            covered[key] = covered.get(key, False) or m[2] == "covered"
    found = set()
    for (ln, col), (t, f) in taken.items():
        if not (t and f):
            way = "never taken" if not (t or f) else ("never true" if not t else "never false")
            found.add((ln, col, f"branch {way}"))
    for key, ok in covered.items():
        if not ok and key in conditions:
            ln, col = conditions[key]
            found.add((ln, col, "condition never shown to decide alone (MC/DC)"))
    return source, sorted(found)


def uncovered(shown):
    """The lines of `llvm-cov show` output with a gap (see gaps()), each with its notes."""
    source, found = gaps(shown)
    out = []
    last = None
    for ln, col, note in found:
        if ln != last:
            out.append(f"{ln:>5}: {source.get(ln, '')}")
            last = ln
        out.append(f"       column {col}: {note}")
    return "\n".join(out)
# [/snippet:uncovered]


if __name__ == "__main__":
    main()
