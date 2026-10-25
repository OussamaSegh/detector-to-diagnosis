#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks MiniDAQ's tool list, docs/regulatory/verification/tools.json (Chapter 20).

    check_tools.py ROOT [--write | --check] [--environment]

Every tool has an ID, a class (T1, T2 or T3), a use, the effect of a defect in it, and, for T2
and T3, the reasons for confidence, evidence that exists in the repository, and what shows the
tool can report a failure (`shown_to_fail`: a fault of tools/gate_selftest.py, a test, a path
or a problem report). --write regenerates tools.md from the list and --check fails if it is out
of date. --environment runs each tool's version command and fails if the installed version
does not match the recorded one: a new compiler on a CI runner is a change to the tools, and
it is noticed by the next run instead of by the next release.
"""
import json
import pathlib
import re
import subprocess
import sys

LIST = pathlib.Path("docs/regulatory/verification/tools.json")
TABLE = pathlib.Path("docs/regulatory/verification/tools.md")
FIELDS = ("id", "name", "kind", "class", "version", "use", "failure", "confidence", "evidence", "shown_to_fail")
CLASSES = {"T1": "no effect on the product or the evidence", "T2": "can fail to reveal a defect",
           "T3": "makes part of the product"}


def test_names(root):
    """Names that a test can be referred to by: Suite.Name of GoogleTest, Class.method of
    unittest, and the names of CTest tests and exercise variants."""
    names = set()
    for f in list((root / "minidaq/tests").rglob("*.cpp")) + list((root / "exercises").rglob("*.cpp")):
        names |= {f"{a}.{b}" for a, b in re.findall(r"^TEST(?:_F)?\((\w+),\s*(\w+)\)", f.read_text(), re.M)}
    for f in list((root / "tools").glob("test_*.py")) + list((root / "minidaq/tests/system").glob("test_*.py")):
        cls = None
        for line in f.read_text().splitlines():
            m = re.match(r"class (\w+)\(", line)
            if m:
                cls = m.group(1)
            m = re.match(r"    def (test_\w+)\(", line)
            if m and cls:
                names.add(f"{cls}.{m.group(1)}")
    for f in root.rglob("CMakeLists.txt"):
        if ".deps" in f.parts or "build" in f.parts:
            continue
        names |= set(re.findall(r"add_test\(NAME\s+([\w./-]+)", f.read_text()))
    return names


def fault_ids(root):
    return set(re.findall(r'^\s+Fault\("(\w+)"', (root / "tools/gate_selftest.py").read_text(), re.M))


def problem_reports(root):
    return {r["id"] for r in json.loads((root / "docs/regulatory/problem-reports.json").read_text())["reports"]}


# [snippet:check]
def check_list(root, tools):
    errors = []
    tests, faults, reports = test_names(root), fault_ids(root), problem_reports(root)
    seen = set()
    for t in tools:
        tid = t.get("id", "?")
        missing = [f for f in FIELDS if f not in t]
        if missing:
            errors.append(f"{tid}: missing {', '.join(missing)}")
            continue
        if tid in seen:
            errors.append(f"{tid}: used twice")
        seen.add(tid)
        if t["class"] not in CLASSES:
            errors.append(f"{tid}: class {t['class']} is not one of {', '.join(CLASSES)}")
        if t["class"] == "T1":
            continue
        if not t["confidence"] or not t["evidence"]:
            errors.append(f"{tid}: a {t['class']} tool needs reasons for confidence and evidence")
        for path in t["evidence"]:
            if not (root / path).exists():
                errors.append(f"{tid}: evidence {path} does not exist")
        s = t["shown_to_fail"]
        if not (s in faults or s in tests or s in reports or (s and (root / s).exists())):
            errors.append(f"{tid}: shown_to_fail '{s}' is no self-test fault, test, path or problem report")
    return errors
# [/snippet:check]


def markdown(tools):
    lines = ["# MiniDAQ tool list", "",
             "Generated from `tools.json` by `tools/check_tools.py --write`; edit the JSON. Classes: "
             + "; ".join(f"**{k}** {v}" for k, v in CLASSES.items()) + ".", "",
             "| ID | Tool | Class | Version | Use | A defect would | Confidence | Shown to fail by |",
             "|---|---|---|---|---|---|---|---|"]
    for t in tools:
        confidence = " ".join(t["confidence"])
        lines.append(f"| {t['id']} | {t['name']} | {t['class']} | {t['version']} | {t['use']} | {t['failure']} | "
                     f"{confidence} | {t['shown_to_fail'] or 'n/a'} |")
    return "\n".join(lines) + "\n"


# [snippet:environment]
def check_environment(tools):
    errors = []
    for t in tools:
        v = t.get("version_check")
        if not v:
            continue
        try:
            out = subprocess.run(v["command"], capture_output=True, text=True, timeout=30).stdout
        except OSError as e:
            errors.append(f"{t['id']} {t['name']}: {v['command'][0]} not found ({e.strerror})")
            continue
        first = out.strip().splitlines()[0] if out.strip() else ""
        ok = re.search(v["pattern"], out) is not None
        print(f"{'ok  ' if ok else 'FAIL'}  {t['id']} {t['name']}: {first}")
        if not ok:
            errors.append(f"{t['id']} {t['name']}: installed '{first}', recorded {t['version']}")
    return errors
# [/snippet:environment]


def main(argv):
    root = pathlib.Path(argv[1]) if len(argv) > 1 and not argv[1].startswith("--") else pathlib.Path(".")
    tools = json.loads((root / LIST).read_text())["tools"]
    errors = check_list(root, tools)
    table = markdown(tools) if not errors else None
    if "--write" in argv and table:
        (root / TABLE).write_text(table)
    if "--check" in argv and table and (not (root / TABLE).exists() or (root / TABLE).read_text() != table):
        errors.append(f"{TABLE} is out of date: run tools/check_tools.py . --write")
    if "--environment" in argv:
        errors += check_environment(tools)
    for e in errors:
        print(e)
    print(f"tool list: {len(tools)} tools, {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
