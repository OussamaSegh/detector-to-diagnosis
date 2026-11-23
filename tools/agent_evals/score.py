#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Scores a subagent's report against the expected findings of its eval (CR-0036, roadmap
2.2.0, Theme P2).

    score.py CASES.json CASE_ID REPORT      one report: FOUND or MISSED for each finding
    score.py CASES.json --prompt CASE_ID    the change to give the subagent: the case's patch

An eval is run by hand: the person gives the subagent each case's change, saves its report, and
scores it; the reports and the scores are kept as evidence. A finding is matched by a line that
starts with its number and names each of its mentions. A report for a case whose expected
findings are "none" must say "No findings" and number none. A finding the case does not expect
is listed as EXTRA, for the person to judge: the eval measures what the subagent finds, and a
person decides whether an extra finding is right.

Exit status 0 if every expected finding is found, 1 if one is missed, 2 on a usage error.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
NUMBERED = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?(?:finding\s*)?\[?(\d)[.):\]]", re.I)


def numbered(report):
    """[(number, line)] for every line of the report that starts with a finding's number."""
    out = []
    for line in report.splitlines():
        m = NUMBERED.match(line)
        if m:
            out.append((int(m.group(1)), line))
    return out


def score(case, report):
    """([(verdict, text)], ok)."""
    lines = numbered(report)
    if case["expected"] == "none":
        ok = "no findings" in report.lower() and not lines
        return [("FOUND" if ok else "MISSED", "no findings")] + \
            [("EXTRA", line.strip()) for _, line in lines], ok
    results, used = [], set()
    for exp in case["expected"]:
        hit = next((i for i, (n, line) in enumerate(lines)
                    if n == exp["finding"] and all(m in line for m in exp["mentions"])), None)
        results.append(("FOUND" if hit is not None else "MISSED",
                        f"{exp['finding']}: {', '.join(exp['mentions'])}"))
        if hit is not None:
            used.add(hit)
    results += [("EXTRA", line.strip()) for i, (_, line) in enumerate(lines) if i not in used]
    return results, all(v == "FOUND" for v, _ in results if v != "EXTRA")


def main(argv):
    if len(argv) < 4:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    spec = json.loads(pathlib.Path(argv[1]).read_text())
    if argv[2] == "--prompt":
        case = next(c for c in spec["cases"] if c["id"] == argv[3])
        print((ROOT / case["patch"]).read_text(), end="")
        return 0
    case = next((c for c in spec["cases"] if c["id"] == argv[2]), None)
    if case is None:
        print(f"no case {argv[2]}", file=sys.stderr)
        return 2
    results, ok = score(case, pathlib.Path(argv[3]).read_text())
    for verdict, text in results:
        print(f"{verdict:7} {text}")
    print(f"{case['id']}: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
