#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks MiniDAQ's change requests in docs/regulatory/changes/ (Chapter 16).

A change request CR-NNNN-name.md follows template.md: a title "# CR-NNNN: ...", a table of
fields (Status, Requested, Source, Decision, Commits) and the sections of the template, none
empty. This tool checks that, and that what a request names exists: SRS requirements, hazards
(H-nn) and risk controls (RC-nn) of the risk file, and, for an implemented request, its commits
in git and the tests it lists (Suite.Name) among MiniDAQ's GoogleTest tests.

Usage: check_changes.py ROOT. Exit status 0 if every change request is consistent.
"""
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from trace_matrix import SRS, parse_srs  # noqa: E402

CHANGES = pathlib.Path("docs/regulatory/changes")
RISK = pathlib.Path("docs/regulatory/risk/hazards.json")
FIELDS = ("Status", "Requested", "Source", "Decision", "Commits")
STATUSES = ("proposed", "approved", "rejected", "implemented")
SECTIONS = ("Description", "Reason", "Impact analysis", "Requirements", "Software items and safety class",
            "Risk", "SOUP", "Interfaces and data formats", "Documents", "Regulatory", "Verification", "Decision")
FIELD_ROW = re.compile(r"^\|\s*([A-Za-z]+)\s*\|\s*(.*?)\s*\|\s*$", re.M)
HEADING = re.compile(r"^#{2,3} (.+?)\s*$", re.M)
TEST_NAME = re.compile(r"\b([A-Z]\w+\.(?:[A-Z]\w+|test_\w+))\b")
GTEST = re.compile(r"^TEST(?:_F)?\((\w+),\s*(\w+)\)", re.M)


def sections(text):
    """Heading -> its text up to the next heading of any level."""
    marks = list(HEADING.finditer(text))
    return {m.group(1): text[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)].strip()
            for i, m in enumerate(marks)}


# [snippet:check]
def check(name, text, known):
    errors = []
    m = re.match(r"# (CR-\d{4}): \S", text)
    if not m or not name.startswith(m.group(1) + "-"):
        return [f"{name}: the title must be '# CR-NNNN: ...' with the number of the file name"]
    fields = dict(FIELD_ROW.findall(text.split("\n## ", 1)[0]))
    for f in FIELDS:
        if not fields.get(f):
            errors.append(f"{name}: no field {f}")
    status = fields.get("Status", "")
    if status not in STATUSES:
        errors.append(f"{name}: status '{status}' is not one of {', '.join(STATUSES)}")
    body = sections(text)
    for s in SECTIONS:
        if s != "Impact analysis" and not body.get(s):
            errors.append(f"{name}: section '{s}' is missing or empty")
    for rid in set(re.findall(r"SRS-[A-Z]+-\d{3}", text)) - known["requirements"]:
        errors.append(f"{name}: {rid} is not a requirement of the SRS")
    for hid in set(re.findall(r"\b(?:H|RC)-\d\d\b", text)) - known["risk"]:
        errors.append(f"{name}: {hid} is not in the risk file")
    if status in ("approved", "implemented", "rejected") and fields.get("Decision", "").startswith("pending"):
        errors.append(f"{name}: status {status}, but the decision is pending")
    if status == "implemented":
        commits = re.findall(r"\b[0-9a-f]{7,40}\b", fields.get("Commits", ""))
        if not commits:
            errors.append(f"{name}: implemented, but no commits")
        for c in commits:
            if not known["commit"](c):
                errors.append(f"{name}: commit {c} is not in the repository")
        tests = TEST_NAME.findall(body.get("Verification", ""))
        if not tests:
            errors.append(f"{name}: implemented, but its verification names no test")
        for t in tests:
            if t not in known["tests"]:
                errors.append(f"{name}: test {t} does not exist")
    return errors
# [/snippet:check]


def tests(root):
    """Every GoogleTest name in minidaq/tests, as Suite.Name, and every unittest of the tools'
    tests (tools/test_*.py), as Class.test_name."""
    names = {f"{s}.{n}" for f in (root / "minidaq/tests").rglob("*.cpp") for s, n in GTEST.findall(f.read_text())}
    for f in (root / "tools").glob("test_*.py"):
        cls = None
        for line in f.read_text().splitlines():
            if m := re.match(r"class (\w+)\(", line):
                cls = m[1]
            elif (m := re.match(r"    def (test_\w+)\(", line)) and cls:
                names.add(f"{cls}.{m[1]}")
    return names


def main(root):
    reqs, _, _ = parse_srs((root / SRS).read_text())
    risk = json.loads((root / RISK).read_text())
    known = {
        "requirements": set(reqs),
        "risk": {h["id"] for h in risk["hazards"]} | {c["id"] for h in risk["hazards"] for c in h["controls"]},
        "tests": tests(root),
        "commit": lambda c: subprocess.run(["git", "-C", str(root), "cat-file", "-e", f"{c}^{{commit}}"],
                                           capture_output=True).returncode == 0,
    }
    errors = []
    files = sorted((root / CHANGES).glob("CR-*.md"))
    numbers = [f.name[:7] for f in files]
    for n in sorted({n for n in numbers if numbers.count(n) > 1}):
        errors.append(f"{n} is used by more than one change request")
    for f in files:
        errors += check(f.name, f.read_text(), known)
    for e in errors:
        print(e)
    print(f"change requests: {len(files)}, " + ("ok" if not errors else f"{len(errors)} problem(s)"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(pathlib.Path(sys.argv[1]).resolve()))
