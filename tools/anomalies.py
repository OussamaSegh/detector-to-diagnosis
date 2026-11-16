#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks MiniDAQ's problem reports and generates the list of known anomalies (Chapter 14).

Every report in docs/regulatory/problem-reports.json has an ID, a title, the item it concerns
and a status. Every report, open or closed, says whether it is relevant to safety and why.
A closed report names the change and how it was verified; an open one records the decision
taken about it. From MDQ-PR-019 on, a closed report also records its root cause analysis
(Chapter 21): the chain of whys from the symptom down, the cause, its category, and why the
defect escaped the checks that should have caught it. From MDQ-PR-065, the first report after
release 1.0.0, and for every open report, a report names the released versions that contain the
defect in "affects" (Chapter 40): a list of versions from CHANGELOG.md, or [] when no release
had it. docs/regulatory/known-anomalies.md, the list a release states as its known
residual anomalies, is generated from the open reports.

Usage: anomalies.py ROOT [--write | --check]
"""
import json
import pathlib
import re
import sys

REPORTS = pathlib.Path("docs/regulatory/problem-reports.json")
OUT = pathlib.Path("docs/regulatory/known-anomalies.md")


# Chapter 21: from MDQ-PR-019 on, a closed report records its root cause analysis.
RCA_FROM = 19
CATEGORIES = ("requirements", "design", "code", "test", "tool", "environment", "process")
# Chapter 40: from MDQ-PR-065 on (the first report after release 1.0.0), and for every open
# report, the released versions that contain the defect.
AFFECTS_FROM = 65
CHANGELOG = pathlib.Path("CHANGELOG.md")


def released_versions(changelog_text):
    """The versions CHANGELOG.md records as released, oldest first."""
    found = re.findall(r"^## \[(\d+\.\d+\.\d+)\] - \d{4}-\d{2}-\d{2}", changelog_text, re.M)
    return sorted(found, key=lambda v: tuple(int(x) for x in v.split(".")))


# [snippet:affects]
def affects_problems(rid, r, releases):
    """A report that must say which releases contain its defect does, with versions that were
    released; [] says no release had it (found before the release that would have shipped it)."""
    number = int(rid[-3:]) if re.fullmatch(r"MDQ-PR-\d{3}", rid) else 0
    if "affects" not in r:
        if number >= AFFECTS_FROM or r.get("status") == "open":
            return [f"{rid}: names the released versions that contain the defect in 'affects' "
                    "([] when none did)"]
        return []
    affects = r["affects"]
    if not isinstance(affects, list) or not all(isinstance(v, str) for v in affects):
        return [f"{rid}: affects is a list of versions"]
    unknown = [v for v in affects if v not in releases]
    if unknown:
        return [f"{rid}: affects names versions that were never released: {', '.join(unknown)}"]
    return []
# [/snippet:affects]


# [snippet:root_cause]
def root_cause_problems(rid, r):
    rc = r.get("root_cause")
    number = int(rid[-3:]) if re.fullmatch(r"MDQ-PR-\d{3}", rid) else 0
    if rc is None:
        if r.get("status") == "closed" and number >= RCA_FROM:
            return [f"{rid}: a closed report from MDQ-PR-{RCA_FROM:03d} on has a root_cause"]
        return []
    errors = []
    whys = rc.get("whys")
    if not isinstance(whys, list) or len(whys) < 2 or not all(isinstance(w, str) and w.strip() for w in whys):
        errors.append(f"{rid}: root_cause.whys is a list of at least two answers, from the symptom down")
    for key in ("cause", "escape"):
        if not str(rc.get(key, "")).strip():
            errors.append(f"{rid}: root_cause.{key} is missing")
    if rc.get("category") not in CATEGORIES:
        errors.append(f"{rid}: root_cause.category is one of {', '.join(CATEGORIES)}")
    return errors
# [/snippet:root_cause]


# [snippet:validate]
def problems(reports, releases=()):
    errors = []
    seen = set()
    for r in reports:
        rid = r.get("id", "?")
        if not re.fullmatch(r"MDQ-PR-\d{3}", rid):
            errors.append(f"{rid}: ID must look like MDQ-PR-nnn")
        if rid in seen:
            errors.append(f"{rid}: duplicate ID")
        seen.add(rid)
        for key in ("title", "found", "item", "description"):
            if not str(r.get(key, "")).strip():
                errors.append(f"{rid}: no {key}")
        ev = r.get("evaluation", {})
        if not isinstance(ev.get("safety_relevant"), bool) or not str(ev.get("rationale", "")).strip():
            errors.append(f"{rid}: evaluation needs safety_relevant (true or false) and a rationale")
        status = r.get("status")
        if status == "closed":
            res = r.get("resolution", {})
            if not res.get("change") or not res.get("verification"):
                errors.append(f"{rid}: a closed report names its change and its verification")
        elif status == "open":
            if not str(r.get("decision", "")).strip():
                errors.append(f"{rid}: an open report records the decision taken about it")
        else:
            errors.append(f"{rid}: status must be 'open' or 'closed'")
        errors += root_cause_problems(rid, r)
        errors += affects_problems(rid, r, releases)
    return errors
# [/snippet:validate]


def span(versions):
    """The versions as a reader scans them: "0.8.0 to 1.3.0" for a run of five, else a list."""
    if not versions:
        return "none"
    if len(versions) <= 2:
        return ", ".join(versions)
    return f"{versions[0]} to {versions[-1]} ({len(versions)} releases)"


def render(reports):
    open_ = sorted((r for r in reports if r.get("status") == "open"), key=lambda r: r["id"])
    lines = [
        "# MiniDAQ known anomalies",
        "",
        "Generated by `tools/anomalies.py --write` from [the problem reports](problem-reports.json).",
        "Do not edit by hand: the test `docs.anomalies` fails when this file is out of date.",
        "",
        f"{len(open_)} open problem reports, "
        f"{sum(1 for r in open_ if r['evaluation']['safety_relevant'])} of them relevant to safety.",
        "",
        "| ID | Item | Anomaly | In releases | Relevant to safety | Why | Decision |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in open_:
        ev = r["evaluation"]
        lines.append(f"| {r['id']} | {r['item']} | {r['title']} | {span(r['affects'])} | "
                     f"{'yes' if ev['safety_relevant'] else 'no'} | "
                     f"{ev['rationale']} | {r['decision']} |")
    return "\n".join(lines) + "\n"


def main(argv):
    root = pathlib.Path(argv[1]).resolve()
    reports = json.loads((root / REPORTS).read_text())["reports"]
    errors = problems(reports, released_versions((root / CHANGELOG).read_text()))
    text = render(reports) if not errors else ""
    mode = argv[2] if len(argv) > 2 else ""
    if errors:
        pass
    elif mode == "--write":
        (root / OUT).write_text(text)
    elif mode == "--check":
        if not (root / OUT).exists() or (root / OUT).read_text() != text:
            errors.append(f"{OUT} is out of date: run tools/anomalies.py . --write")
    else:
        sys.stdout.write(text)
    for e in errors:
        print(e, file=sys.stderr)
    print(f"anomalies: {len(reports)} reports, {len(errors)} problem(s)", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
