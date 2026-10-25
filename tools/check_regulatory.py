#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks the regulatory file in docs/regulatory/ (Chapter 13 onward).

- The intended-use statement has every section a reviewer looks for.
- Every relative link in the regulatory documents points to a file that exists.
- The standards map's SVG was regenerated after the last change to its DOT source (every node
  of the source is in the picture), and the map agrees with Exercise 13.1's solution.

Usage: check_regulatory.py REPO_ROOT. Exit status 0 if everything holds, 1 otherwise.
"""
import pathlib
import re
import sys

INTENDED_USE_SECTIONS = [
    "Intended purpose",
    "Intended users",
    "Patient population",
    "Use environment",
    "Principle of operation",
    "Contraindications and limitations",
    "Data",
    "What MiniDAQ is not",
]

LINK = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")
DOT_NODE = re.compile(r"^\s*(\w+)\s*\[label=", re.M)
DOT_EDGE = re.compile(r"^\s*(\w+)\s*->\s*(\w+)\s*\[label=\"(\w+)\"\]", re.M)


def headings(text):
    return re.findall(r"^##\s+(.*?)\s*$", text, re.M)


def main(root):
    reg = root / "docs" / "regulatory"
    errors = []

    use = (reg / "intended-use.md").read_text()
    have = headings(use)
    for s in INTENDED_USE_SECTIONS:
        if s not in have:
            errors.append(f"intended-use.md: missing section '## {s}'")
    if "not a medical device" not in use:
        errors.append("intended-use.md: must say that MiniDAQ is not a medical device")

    for md in sorted(reg.rglob("*.md")):
        for target in LINK.findall(md.read_text()):
            if re.match(r"^[a-z]+:", target):
                continue  # http:, https:, mailto:
            if not (md.parent / target).exists():
                errors.append(f"{md.relative_to(root)}: broken link to {target}")

    dot = (reg / "standards-map.dot").read_text()
    svg = (reg / "standards-map.svg").read_text()
    for node in DOT_NODE.findall(dot):
        if f"<title>{node}</title>" not in svg:
            errors.append(f"standards-map.svg: node {node} missing; regenerate with "
                          "dot -Tsvg standards-map.dot -o standards-map.svg")
    solution = root / "exercises" / "ch13" / "e1_standards_map" / "solution" / "standards.dot"
    if set(DOT_EDGE.findall(dot)) != set(DOT_EDGE.findall(solution.read_text())):
        errors.append("standards-map.dot and Exercise 13.1's solution disagree")

    for e in errors:
        print(e)
    print("regulatory file: " + ("ok" if not errors else f"{len(errors)} problem(s)"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(pathlib.Path(sys.argv[1]).resolve()))
