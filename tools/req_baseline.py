#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The requirements freeze (Chapter 33): the SRS against its baseline.

A baseline records a digest of every requirement of the SRS (its text, item and method) at the
moment the requirements were frozen. From then on a requirement that is added, changed, withdrawn
or removed must be named by a change request that is approved or implemented: a frozen
requirement changes only through change control, never as a side effect of an edit.

    tools/req_baseline.py ROOT --check     # exit 1 for every difference no change request names
    tools/req_baseline.py ROOT --diff      # list the differences and the requests that name them
    tools/req_baseline.py ROOT --write     # take a new baseline (at a release, after the review)

The baseline is docs/regulatory/srs-baseline.json; the change requests are
docs/regulatory/changes/CR-*.md, and a request names a requirement when its ID appears anywhere in
its text.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

SRS = "docs/regulatory/srs.md"
BASELINE = "docs/regulatory/srs-baseline.json"
CHANGES = "docs/regulatory/changes"
ROW = re.compile(r"^\|\s*(SRS-[A-Z]+-\d{3})\s*\|\s*(.*?)\s*\|\s*([\w-]+)\s*\|\s*([A-Z, ]+)\s*\|\s*$")
ID = re.compile(r"SRS-[A-Z]+-\d{3}")
STATUS = re.compile(r"^\|\s*Status\s*\|\s*(\w+)\s*\|", re.M)
ACCEPTED = {"approved", "implemented"}


# [snippet:digest]
def requirements(srs_text):
    """{id: digest} of every requirement row of the SRS. The digest covers the text, the item and
    the method, with runs of white space made one space, so that rewrapping a table changes
    nothing and changing a word changes the digest."""
    out = {}
    for line in srs_text.splitlines():
        m = ROW.match(line)
        if m:
            text = " ".join(" | ".join(m.group(2, 3, 4)).split())
            out[m.group(1)] = hashlib.sha256(text.encode()).hexdigest()[:16]
    return out
# [/snippet:digest]


def differences(baseline, current):
    """[(id, how)] with how in added, changed, removed; sorted by id."""
    out = [(r, "added") for r in current if r not in baseline]
    out += [(r, "changed") for r in current if r in baseline and current[r] != baseline[r]]
    out += [(r, "removed") for r in baseline if r not in current]
    return sorted(out)


def change_requests(root):
    """{requirement id: [CR names that are approved or implemented and name it]}."""
    named = {}
    for cr in sorted((root / CHANGES).glob("CR-*.md")):
        text = cr.read_text()
        m = STATUS.search(text)
        if not m or m.group(1) not in ACCEPTED:
            continue
        for rid in set(ID.findall(text)):
            named.setdefault(rid, []).append("-".join(cr.name.split("-")[:2]))
    return named


# [snippet:check]
def check(root):
    """(problems, rows): a problem for every difference that no accepted change request names."""
    base = json.loads((root / BASELINE).read_text())
    current = requirements((root / SRS).read_text())
    named = change_requests(root)
    rows, problems = [], []
    for rid, how in differences(base["requirements"], current):
        crs = named.get(rid, [])
        rows.append((rid, how, crs))
        if not crs:
            problems.append(f"{rid} {how} since the baseline ({base['name']}) and named by no "
                            f"approved or implemented change request")
    return problems, rows
# [/snippet:check]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", type=pathlib.Path)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--diff", action="store_true")
    mode.add_argument("--write", metavar="NAME", help="name of the new baseline")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    if args.write:
        srs = (root / SRS).read_text()
        version = re.search(r"^Version (\d+)", srs, re.M)
        data = {"comment": "The requirements freeze (Chapter 33): a digest of every SRS requirement "
                           "when the baseline was taken. tools/req_baseline.py --check fails for "
                           "every requirement added, changed or removed since, that no approved or "
                           "implemented change request names.",
                "name": args.write, "srs_version": int(version.group(1)) if version else None,
                "requirements": requirements(srs)}
        (root / BASELINE).write_text(json.dumps(data, indent=1, sort_keys=False) + "\n")
        print(f"baseline {args.write}: {len(data['requirements'])} requirements")
        return 0
    problems, rows = check(root)
    if args.diff:
        for rid, how, crs in rows:
            print(f"{rid:14} {how:8} {', '.join(crs) or '(no change request)'}")
    for p in problems:
        print(p, file=sys.stderr)
    print(f"requirements against the baseline: {len(rows)} difference(s), {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
