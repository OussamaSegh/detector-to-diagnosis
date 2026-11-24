#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Writes the skeleton of a release record from the release checks' output, and checks a record
(roadmap 2.0.0, Theme D).

Each release record (docs/regulatory/releases/X.Y.Z.md) was written by hand from
measurements/release-X.Y.Z/, row by row; a row's evidence path or result could be copied
wrong. The skeleton takes from the evidence what a program can know: the commit of part 1, the
result of every check in release-checks.txt (the last run of each part counts), the evidence
file of each row, the acceptance verdict, the open problem reports and the build commands. What
needs a person (the notes on the results, the risk and SOUP judgments, the audit, the
documents' approval) is left as a line starting "TODO(record):", and `check` refuses a record
that still has one.

Usage:
  release_record.py skeleton ROOT VERSION      prints the skeleton; the evidence is read from
                                               ROOT/measurements/release-VERSION/
  release_record.py check ROOT RECORD...       Exercise 14.5's check, plus no TODO(record) left

Exit status 0 on success, 1 on a problem.
"""
import importlib.util
import json
import pathlib
import re
import sys

# The facts the release checks run, from the file they share (CAPA-0007).
FACTS = json.loads((pathlib.Path(__file__).resolve().parent / "release_facts.json").read_text())
PRESETS = FACTS["presets"]
TODO = "TODO(record):"
# (row of the record, the release check lines it rests on (prefixes), evidence file)
ROWS = [(f"build {p}", ["build and tests, six presets"], "run_all.txt") for p in PRESETS] + \
       [(f"tests {p}", ["build and tests, six presets"], "run_all.txt") for p in PRESETS] + [
    ("static analysis", ["static analysis"], "static-analysis.txt"),
    ("product build without the simulator", ["product build and its tests"], "product.txt"),
    ("trace matrix", ["build and tests, six presets"], "run_all.txt"),
    ("exercise starters", ["starters fail"], "starters.txt"),
    ("stress run", ["stress run"], "stress-tsan.txt"),
    ("property-based tests, wide search", ["property-based tests, wide search"], "properties-wide.txt"),
    ("structural coverage", ["coverage report", "Exercise 18.3"], "coverage.txt"),
    ("performance", ["performance regression gate"], "perf-gate.txt"),
    ("performance, SRS-PERF-020", ["pipeline benchmark ran"], "perf-pipeline.txt"),
    ("performance, SRS-PERF-021", ["writer benchmark ran"], "perf-writer.txt"),
    ("performance, SRS-PERF-022", ["soak"], "soak.txt"),
    ("system tests", ["system test report"], "system-test-report.md"),
    (f"soak, {FACTS['soak_minutes']} minutes", ["soak"], "soak.txt"),
    ("end to end", ["end to end"], "e2e.txt"),
    ("fuzzing", ["fuzz_", "fuzz build"], "release-checks.txt"),
]


SOAK_ROW = f"soak, {FACTS['soak_minutes']} minutes"


def soak_label(found):
    """The soak row's label with the length the release's own soak check names (MDQ-PR-090):
    30 minutes until 2.0.1, 100 since CR-0035. Without a soak line, the current length."""
    for name in found:
        m = re.match(r"soak, (\d+) minutes", name)
        if m:
            return f"soak, {m.group(1)} minutes"
    return SOAK_ROW


def results(release_checks):
    """{check line's name: 'pass' or 'FAIL'}; a part run again replaces its earlier lines."""
    out = {}
    for line in release_checks.splitlines():
        m = re.match(r"(pass|FAIL)  (.+)$", line)
        if m:
            out[m.group(2)] = m.group(1)
    return out


def row_result(found, prefixes):
    matched = [r for name, r in found.items() if any(name.startswith(p) for p in prefixes)]
    if not matched:
        return "not run"
    return "pass" if all(r == "pass" for r in matched) else "FAIL"


def acceptance(evidence):
    """(row result, verdict line) from acceptance.md, or None if it was not evaluated."""
    path = evidence / "acceptance.md"
    if not path.is_file():
        return None
    text = path.read_text()
    m = re.search(r"^(\d+) pass, (\d+) fail, (\d+) missing, (\d+) stale\.", text, re.M)
    if not m:
        return "FAIL", "no verdict line"
    ok = int(m.group(2)) == int(m.group(3)) == int(m.group(4)) == 0
    return ("pass" if ok else "FAIL"), m.group(0)


def table_rows(root, version):
    """The rows of the record's table of checks, as the evidence gives them."""
    rel = f"measurements/release-{version}"
    evidence = root / rel
    found = results((evidence / "release-checks.txt").read_text())
    path = f"../../{rel}"
    soak = soak_label(found)
    rows = [f"| {soak if name == SOAK_ROW else name} | {row_result(found, prefixes)} | `{path}/{file}` |"
            for name, prefixes, file in ROWS]
    rows.insert([name for name, _, _ in ROWS].index("performance") + 1, f"| performance trend against the baseline | recorded | `{path}/perf-trend.txt` |")
    acc = acceptance(evidence)
    rows.append(f"| acceptance | {acc[0]} | `{path}/acceptance.md` |" if acc else
                f"| acceptance | not run | `{path}/acceptance.md` |")
    for name, file in (("reproducible build", "repro/repro.txt"), ("CI on GitHub", "ci-run.txt")):
        rows.append(f"| {name} | {'pass' if (evidence / file).is_file() else 'not run'} | `{path}/{file}` |")
    return rows


def skeleton(root, version):
    rel = f"measurements/release-{version}"
    evidence = root / rel
    commit_file = evidence / "commit.txt"
    if not (evidence / "release-checks.txt").is_file() or not commit_file.is_file():
        raise ValueError(f"{rel}: no release-checks.txt or commit.txt; run tools/release_checks.sh first")
    commit = commit_file.read_text().split()[1]
    rows = table_rows(root, version)
    parts = sorted(set(re.findall(r"all release checks passed \(part (\w+)\)",
                                  (evidence / "release-checks.txt").read_text())))
    reports = json.loads((root / "docs/regulatory/problem-reports.json").read_text())["reports"]
    open_reports = [r for r in reports if r["status"] == "open"]
    anomalies = "\n".join(f"- {r['id']} ({r.get('item', '?')}): {r.get('title', r.get('summary', ''))}. "
                          f"{TODO} released with, because ..." for r in open_reports) or "None open."
    major_minor = ".".join(version.split(".")[:2])
    return f"""# MiniDAQ {version} release record

The record of SDP section 8 for release {version}: {TODO} what this release is. Evidence paths
are relative to this directory's parent, `docs/regulatory/`; the files are in `{rel}/` and were
written by `tools/release_checks.sh` unless the notes below say otherwise. Checked with
`tools/release_record.py check` (Exercise 14.5's `check()`) before the tag was made.

## Release

MiniDAQ {version}, commit {commit}, tag book-v{version}

The release checks ran on this commit with a clean working tree (`commit.txt`); the parts that
passed: {", ".join(parts) or "none"} (`release-checks.txt`). {TODO} what changed since the
previous release, and the commits on top of this one up to the tag.

## Verification

Notes on the results:

- {TODO} one note per check, with its numbers from the evidence.

| Check | Result | Evidence |
|---|---|---|
""" + "\n".join(rows) + f"""

## Internal audit

{TODO} the internal audit held before the release checks (SDP section 8, item 9).

## Corrective actions

{TODO} each open CAPA and its effectiveness check due at this release (`docs.capa`).

## Documents

{TODO} the controlled documents of the design file released with {version}, at their versions.

## Known anomalies

Generated from the problem reports by `tools/anomalies.py` ([known-anomalies.md](../known-anomalies.md)):
{len(open_reports)} open report(s), each evaluated again for this release.

{anomalies}

## Risk

{TODO} the hazards, the threat model's review for this release and the overall residual risk.

## SOUP review

{TODO} YYYY-MM-DD, for MiniDAQ {major_minor} ([SOUP list](../soup-list.md), test `docs.soup`).

## Requirements

{TODO} the SRS version and its baseline (`docs.baseline`).

## Build

The release is built from the tag with the presets, as the checks did:

```sh
git checkout book-v{version}
ci/run_all.sh                                     # the six presets, tests and documentation tests
ci/run_all.sh product                             # the product build, without the simulator
tools/static_analysis.sh build/clang-release
cmake --preset product && cmake --build --preset product     # the shipped binaries (CR-0029)
tools/repro_check.sh OUT                                     # two builds, compared byte for byte
tools/make_sbom.py --validate -o minidaq-{version}.cdx.json
tools/release_checks.sh OUT {FACTS['fuzz_seconds']} resume                        # this record's evidence
tools/acceptance.py OUT                                       # the acceptance verdict
book/build.sh all both && book/build.sh boox both             # the book and the solutions
```

## Archive

- Source with its full git history and tags: `minidaq-v{version}.zip`.
- Book and solutions: `detector-to-diagnosis-v{version}.epub` and `.pdf`,
  `detector-to-diagnosis-solutions-v{version}.epub` and `.pdf`; the Boox PDFs; the KDP interiors
  and covers.
- SBOM: `minidaq-{version}.cdx.json` (CycloneDX 1.5).
- The product archive of the reproducible build, its SHA-256 in `repro/repro.txt`.
"""


def exercise_check(root):
    path = root / "exercises/ch14/e5_release_check/solution/release_check.py"
    spec = importlib.util.spec_from_file_location("release_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.check


# The first release whose record has every row the skeleton writes today: the product preset's
# row came with CR-0029 in 2.0.0, and the rows of earlier records follow the rules of their time.
FIRST_TABLE = (2, 0, 0)


def table_drift(root, record, text):
    """The rows the evidence gives that the record's table lacks or states otherwise
    (MDQ-PR-089: the 2.1.0 record kept a soak row of 30 minutes next to a soak of 100). A record
    may add rows; each row the skeleton would write must be in it as written."""
    version = record.stem
    if not (root / f"measurements/release-{version}/release-checks.txt").is_file():
        return []  # a record without its evidence in the tree; the exercise check reports paths
    if tuple(int(x) for x in version.split(".")) < FIRST_TABLE:
        return []  # written before the table had its present rows (MDQ-PR-090)
    lines = {line.strip() for line in text.splitlines()}
    named = {line for line in lines if (m := DEVIATED.match(line)) and decided(text, m.group(1))}
    lines |= {DEVIATED.sub(r"| \1 | pass |", line) for line in named}
    lines |= {DEVIATED.sub(r"| \1 | FAIL |", line) for line in named}
    return [f"the table lacks the row {row} that the evidence gives"
            for row in table_rows(root, version) if row not in lines]


# A check that failed and was released with the software lead's decision (SDP section 8): its row
# says "fail (deviation)" and the record has a section Deviation with the decision (MDQ-PR-098).
DEVIATED = re.compile(r"^\| ([^|]+?) \| fail \(deviation\) \|")


def deviation(text):
    """The text of the record's section Deviation, empty if it has none."""
    m = re.search(r"^## Deviation\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1).strip() if m else ""


def decided(text, row):
    """Whether the section Deviation names the row, as `row`: a decision excuses only the checks
    it names, not every row marked so (review of 2.2.0, MDQ-PR-099)."""
    return f"`{row}`" in deviation(text)


def excused(text, errors):
    """The exercise check's errors without those of the rows released with a deviation that
    the section Deviation names."""
    def released(e):
        m = re.fullmatch(r"Verification: '([^']+)' is 'fail \(deviation\)', not 'pass'", e)
        return m is not None and decided(text, m.group(1))
    return [e for e in errors if not released(e)]


def check(root, record):
    text = record.read_text()
    errors = excused(text, exercise_check(root)(text, root / "docs/regulatory"))
    errors += table_drift(root, record, text)
    errors += [f"line {n}: still a {TODO} line" for n, line in enumerate(text.splitlines(), 1)
               if TODO in line]
    return errors


def main(argv):
    if len(argv) < 4 or argv[1] not in ("skeleton", "check"):
        print(__doc__)
        return 1
    root = pathlib.Path(argv[2]).resolve()
    try:
        if argv[1] == "skeleton":
            sys.stdout.write(skeleton(root, argv[3]))
            return 0
    except ValueError as e:
        print(e)
        return 1
    status = 0
    for name in argv[3:]:
        errors = check(root, pathlib.Path(name))
        for e in errors:
            print(f"{name}: {e}")
        print(f"{name}: " + ("ok" if not errors else f"{len(errors)} problem(s)"))
        status |= bool(errors)
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv))
