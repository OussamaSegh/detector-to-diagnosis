#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Generates MiniDAQ's trace matrix from the SRS and the requirement tags in the tests (Chapter 14).

The requirements are the rows of docs/regulatory/srs.md (see tools/req_lint.py for their form).
A test names the requirements it verifies with a comment in its body:

    TEST(CoincidenceSorter, TheWindowIsInclusive) {
      // REQ: SRS-SRT-001

or, in Python, `# REQ: SRS-...` inside a `def test_...`. One comment may list several IDs,
separated by commas. The matrix lists tests by file and name, not by line number, so that
moving a test does not change the matrix.

The tool fails if
- a requirement verified by test (method T) has no test,
- a test names a requirement that the SRS does not define, or one that is withdrawn,
- a requirement verified another way has no entry in the SRS's evidence table,
- an ID is defined twice,
- with --check, the committed matrix differs from the one the sources produce.

The column "Risk controls" lists the controls of docs/regulatory/risk/hazards.json that a
requirement implements (Chapter 15); tools/check_risk.py checks the controls themselves.

Usage:
    trace_matrix.py ROOT            print the matrix
    trace_matrix.py ROOT --write    write docs/regulatory/trace-matrix.md
    trace_matrix.py ROOT --check    fail if docs/regulatory/trace-matrix.md is out of date
"""
import json
import pathlib
import re
import sys

SRS = pathlib.Path("docs/regulatory/srs.md")
MATRIX = pathlib.Path("docs/regulatory/trace-matrix.md")
RISK = pathlib.Path("docs/regulatory/risk/hazards.json")
TEST_DIRS = ["minidaq/tests", "fuzz", "tools"]

# [snippet:parse]
REQ_ROW = re.compile(r"^\|\s*(SRS-[A-Z]+-\d{3})\s*\|\s*(.*?)\s*\|\s*([\w-]+)\s*\|\s*([A-Z, ]+)\s*\|\s*$")
EVIDENCE_ROW = re.compile(r"^\|\s*(SRS-[A-Z]+-\d{3})\s*\|\s*([A-Z, ]+)\s*\|\s*(.+?)\s*\|\s*$")
TAG = re.compile(r"(?://|#)\s*REQ:\s*(SRS-[A-Z]+-\d{3}(?:\s*,\s*SRS-[A-Z]+-\d{3})*)")
CPP_TEST = re.compile(r"^\s*TEST(?:_F|_P)?\(\s*(\w+)\s*,\s*(\w+)\s*\)")
PY_TEST = re.compile(r"^\s*def\s+(test_\w+)\s*\(")


def parse_srs(text):
    """({id: (text, item, methods)}, {id: evidence}, [duplicate ids])."""
    reqs, evidence, dups = {}, {}, []
    for line in text.splitlines():
        m = REQ_ROW.match(line)
        if m:
            rid = m.group(1)
            if rid in reqs:
                dups.append(rid)
            methods = {x.strip() for x in m.group(4).split(",") if x.strip()}
            reqs[rid] = (m.group(2), m.group(3), methods)
            continue
        m = EVIDENCE_ROW.match(line)
        if m:
            evidence[m.group(1)] = m.group(3)
    return reqs, evidence, dups


def find_tags(rel_path, text):
    """[(requirement id, test name, file)] for every tag in one source file."""
    out = []
    current = None
    for line in text.splitlines():
        m = CPP_TEST.match(line)
        if m:
            current = f"{m.group(1)}.{m.group(2)}"
        m = PY_TEST.match(line)
        if m:
            current = m.group(1)
        for group in TAG.findall(line):
            for rid in re.split(r"\s*,\s*", group):
                out.append((rid, current or "(outside a test)", rel_path))
    return out
# [/snippet:parse]


def scan(root):
    tags = []
    for d in TEST_DIRS:
        base = root / d
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if p.suffix not in {".cpp", ".hpp", ".py"} or "__pycache__" in p.parts:
                continue
            if p.resolve() == pathlib.Path(__file__).resolve():
                continue  # this file's docstring shows the tag syntax
            tags.extend(find_tags(p.relative_to(root).as_posix(), p.read_text(errors="replace")))
    return tags


# [snippet:check]
def check(reqs, evidence, dups, tags):
    errors = [f"{rid}: defined more than once" for rid in dups]
    tested = {}
    for rid, test, path in tags:
        if rid not in reqs:
            errors.append(f"{path}: {test} names {rid}, which the SRS does not define")
        elif reqs[rid][0].startswith("Withdrawn"):
            errors.append(f"{path}: {test} names {rid}, which is withdrawn")
        else:
            tested.setdefault(rid, set()).add((path, test))
    for rid, (text, _item, methods) in reqs.items():
        if text.startswith("Withdrawn"):
            continue
        if "T" in methods and rid not in tested:
            errors.append(f"{rid}: verified by test, but no test names it")
        if methods - {"T"} and rid not in evidence:
            errors.append(f"{rid}: verified by {','.join(sorted(methods - {'T'}))}, but has no evidence entry")
    return errors, tested
# [/snippet:check]


def risk_controls(root):
    """Requirement ID -> the IDs of the risk controls it implements."""
    path = root / RISK
    out = {}
    if path.exists():
        for h in json.loads(path.read_text())["hazards"]:
            for c in h["controls"]:
                for rid in c.get("requirements", []):
                    out.setdefault(rid, []).append(c["id"])
    return out


def render(reqs, evidence, tested, controls=None):
    controls = controls or {}
    live = {k: v for k, v in reqs.items() if not v[0].startswith("Withdrawn")}
    n_tests = len({t for s in tested.values() for t in s})
    lines = [
        "# MiniDAQ trace matrix",
        "",
        "Generated by `tools/trace_matrix.py --write` from [the SRS](srs.md) and the `REQ:` tags in the",
        "tests. Do not edit by hand: the test `docs.trace` fails when this file is out of date.",
        "",
        f"{len(live)} requirements, {sum(1 for r in live if r in tested)} verified by at least one test, "
        f"{n_tests} tests.",
        "",
        "| Requirement | Item | Method | Verified by | Risk controls |",
        "|---|---|---|---|---|",
    ]
    for rid in sorted(live, key=lambda r: (r.split("-")[1], r)):
        _text, item, methods = live[rid]
        cells = [f"`{path.rsplit('/', 1)[-1]}` {test}" for path, test in sorted(tested.get(rid, ()))]
        if rid in evidence:
            cells.append(evidence[rid].split(":")[0])
        rc = ", ".join(sorted(set(controls.get(rid, []))))
        lines.append(f"| {rid} | {item} | {','.join(sorted(methods))} | {'<br>'.join(cells)} | {rc} |")
    return "\n".join(lines) + "\n"


def main(argv):
    root = pathlib.Path(argv[1]).resolve()
    reqs, evidence, dups = parse_srs((root / SRS).read_text())
    errors, tested = check(reqs, evidence, dups, scan(root))
    matrix = render(reqs, evidence, tested, risk_controls(root))
    mode = argv[2] if len(argv) > 2 else ""
    if mode == "--write":
        (root / MATRIX).write_text(matrix)
    elif mode == "--check":
        committed = (root / MATRIX).read_text() if (root / MATRIX).exists() else ""
        if committed != matrix:
            errors.append(f"{MATRIX} is out of date: run tools/trace_matrix.py . --write")
    else:
        sys.stdout.write(matrix)
    for e in errors:
        print(e, file=sys.stderr)
    print(f"trace: {len(reqs)} requirements, {len(errors)} problem(s)", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
