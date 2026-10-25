#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks MiniDAQ's corrective and preventive actions in docs/regulatory/capa/ (Chapter 16).

A CAPA record CAPA-NNNN-name.md follows template.md: a title "# CAPA-NNNN: ...", a table of
fields (Status, Opened, Source, Owner, Effectiveness check) and the sections of the template,
none empty. This tool checks that, and that:
- the problem reports it names exist and name it back (field "capa" in problem-reports.json),
  and every problem report that names a CAPA is named by it;
- its corrective and preventive actions name at least one file of the repository that exists
  (an action that changes nothing on record is an intention), unless the preventive action is
  "none" with a reason;
- its root cause is not "human error" or one of its synonyms;
- its effectiveness check states a criterion and a due date, and a closed CAPA its result.

Usage: check_capa.py ROOT. Exit status 0 if every CAPA record is consistent.
"""
import json
import pathlib
import re
import subprocess
import sys

CAPA = pathlib.Path("docs/regulatory/capa")
REPORTS = pathlib.Path("docs/regulatory/problem-reports.json")
FIELDS = ("Status", "Opened", "Source", "Owner", "Effectiveness check")
STATUSES = ("open", "implemented", "closed")
SECTIONS = ("Problem", "Investigation", "Root cause", "Correction", "Corrective action", "Preventive action",
            "Verification of the actions", "Effectiveness check", "Closure")
FIELD_ROW = re.compile(r"^\|\s*([A-Za-z ]+?)\s*\|\s*(.*?)\s*\|\s*$", re.M)
HEADING = re.compile(r"^## (.+?)\s*$", re.M)
PATH = re.compile(r"`([\w./-]+/[\w./-]*|[\w-]+\.(?:md|json|py|cpp|hpp|sh|yml|txt|cmake))`")
BLAME = re.compile(r"\b(human|operator|developer|user) error\b|\bcareless(ness)?\b|\binattention\b", re.I)


def sections(text):
    marks = list(HEADING.finditer(text))
    return {m.group(1): text[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)].strip()
            for i, m in enumerate(marks)}


def files_named(text, files):
    """The repository files (or directories, ending in '/') that a section names in backticks."""
    return [p for p in PATH.findall(text) if p in files or (p.endswith("/") and any(f.startswith(p) for f in files))]


# [snippet:check]
def check(name, text, reports, files):
    m = re.match(r"# (CAPA-\d{4}): \S", text)
    if not m or not name.startswith(m.group(1) + "-"):
        return [f"{name}: the title must be '# CAPA-NNNN: ...' with the number of the file name"]
    capa = m.group(1)
    errors = []
    fields = dict(FIELD_ROW.findall(text.split("\n## ", 1)[0]))
    for f in FIELDS:
        if not fields.get(f):
            errors.append(f"{name}: no field {f}")
    status = fields.get("Status", "")
    if status not in STATUSES:
        errors.append(f"{name}: status '{status}' is not one of {', '.join(STATUSES)}")
    body = sections(text)
    for s in SECTIONS:
        if s != "Closure" and not body.get(s):
            errors.append(f"{name}: section '{s}' is missing or empty")
    named = set(re.findall(r"MDQ-PR-\d{3}", fields.get("Source", "")))
    for rid in sorted(named):
        if rid not in reports:
            errors.append(f"{name}: {rid} is not a problem report")
        elif reports[rid].get("capa") != capa:
            errors.append(f"{name}: {rid} does not name {capa} in its field 'capa'")
    for rid, r in sorted(reports.items()):
        if r.get("capa") == capa and rid not in named:
            errors.append(f"{name}: {rid} names {capa}, but the CAPA's source does not name it")
    if BLAME.search(body.get("Root cause", "")):
        errors.append(f"{name}: the root cause blames a person; ask why the process let the error through")
    if not files_named(body.get("Corrective action", ""), files):
        errors.append(f"{name}: the corrective action names no file of the repository that it changes")
    preventive = body.get("Preventive action", "")
    if not preventive.lower().startswith("none") and not files_named(preventive, files):
        errors.append(f"{name}: the preventive action names no file of the repository, and is not 'none'")
    check_ = body.get("Effectiveness check", "")
    for key in ("Criterion:", "Due:"):
        if key not in check_:
            errors.append(f"{name}: the effectiveness check has no '{key}' line")
    result = re.search(r"^Result:\s*(.*)$", check_, re.M)
    if status == "closed":
        if not result or not result.group(1) or result.group(1).startswith("filled in"):
            errors.append(f"{name}: closed without the result of its effectiveness check")
        if not body.get("Closure"):
            errors.append(f"{name}: closed without a closure record")
    return errors
# [/snippet:check]


def main(root):
    reports = {r["id"]: r for r in json.loads((root / REPORTS).read_text())["reports"]}
    out = subprocess.run(["git", "-C", str(root), "ls-files"], capture_output=True, text=True, check=True)
    files = set(out.stdout.split())
    errors = []
    records = sorted((root / CAPA).glob("CAPA-*.md"))
    numbers = [f.name[:9] for f in records]
    for n in sorted({n for n in numbers if numbers.count(n) > 1}):
        errors.append(f"{n} is used by more than one CAPA")
    for f in records:
        errors += check(f.name, f.read_text(), reports, files)
    for rid, r in sorted(reports.items()):
        if r.get("capa") and r["capa"] not in numbers:
            errors.append(f"{rid}: names {r['capa']}, which does not exist")
    for e in errors:
        print(e)
    print(f"CAPA records: {len(records)}, " + ("ok" if not errors else f"{len(errors)} problem(s)"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(pathlib.Path(sys.argv[1]).resolve()))
