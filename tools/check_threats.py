#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks MiniDAQ's threat model (Chapter 17).

docs/regulatory/security/threats.json lists the elements of the data flow diagram and a
STRIDE analysis of each. This tool checks what can be checked mechanically:

1. The elements of threats.json are the nodes of dataflow.dot, and every flow's ends are
   elements.
2. Every element has at least one threat for every STRIDE category that applies to its kind
   (section "applies"), or an entry with the status "not_applicable".
3. Every threat has a known element, a STRIDE letter that applies to that element's kind, a
   status, and the reasons its status needs: a mitigated threat names requirements of the SRS
   that are verified; an environment threat names a risk control of the information type,
   whose text states the assumption; an accepted or not applicable threat has a note.
4. Every risk control a threat names exists in docs/regulatory/risk/hazards.json.

It cannot tell whether a threat is missing or a mitigation is enough: that is the review of
threat-model.md, section 9.

Usage: check_threats.py ROOT. Exit status 0 if the threat model is consistent.
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from trace_matrix import SRS, parse_srs, scan  # noqa: E402

THREATS = pathlib.Path("docs/regulatory/security/threats.json")
DFD = pathlib.Path("docs/regulatory/security/dataflow.dot")
RISK = pathlib.Path("docs/regulatory/risk/hazards.json")
STATUSES = {"mitigated", "environment", "accepted", "not_applicable"}
NODE = re.compile(r"^\s*([a-z_][a-z0-9_]*)\s*\[", re.M)
EDGE = re.compile(r"^\s*([a-z_][a-z0-9_]*)\s*->\s*([a-z_][a-z0-9_]*)", re.M)


def check_diagram(doc, dot):
    errors = []
    nodes = set(NODE.findall(dot)) - {"graph", "node", "edge"}
    edges = set(EDGE.findall(dot))
    elements = {e["id"]: e for e in doc["elements"]}
    for e in elements.values():
        if e["kind"] == "flow":
            for end in ("from", "to"):
                if e.get(end) not in elements or elements[e[end]]["kind"] == "flow":
                    errors.append(f"{e['id']}: a flow's '{end}' must be an element that is not a flow")
            if (e.get("from"), e.get("to")) not in edges:
                errors.append(f"{e['id']}: the diagram has no edge {e.get('from')} -> {e.get('to')}")
            if not e.get("boundary"):
                errors.append(f"{e['id']}: a flow names the trust boundary it crosses")
        elif e["id"] not in nodes:
            errors.append(f"{e['id']}: not a node of {DFD.name}")
    for n in sorted(nodes - set(elements)):
        errors.append(f"{DFD.name}: node {n} is not an element of {THREATS.name}")
    return errors


# [snippet:coverage]
def check_coverage(doc):
    """Every category that applies to an element's kind is analyzed."""
    errors = []
    for e in doc["elements"]:
        letters = doc["applies"].get(e["kind"])
        if letters is None:
            errors.append(f"{e['id']}: unknown kind {e['kind']}")
            continue
        done = {t["stride"] for t in doc["threats"] if t["element"] == e["id"]}
        for s in letters:
            if s not in done:
                errors.append(f"{e['id']}: no threat of category {s} ({doc['stride'][s].split(':')[0]})")
    return errors
# [/snippet:coverage]


def check_threats(doc, reqs, verified, controls):
    errors = []
    kinds = {e["id"]: e["kind"] for e in doc["elements"]}
    seen = set()
    for t in doc["threats"]:
        tid = t.get("id", "?")
        if tid in seen:
            errors.append(f"{tid}: defined twice")
        seen.add(tid)
        if t.get("element") not in kinds:
            errors.append(f"{tid}: unknown element {t.get('element')}")
            continue
        if t.get("stride") not in doc["applies"][kinds[t["element"]]]:
            errors.append(f"{tid}: category {t.get('stride')} does not apply to a {kinds[t['element']]}")
        if not t.get("threat", "").strip():
            errors.append(f"{tid}: no threat statement")
        status = t.get("status")
        if status not in STATUSES:
            errors.append(f"{tid}: status must be one of {', '.join(sorted(STATUSES))}")
            continue
        # [snippet:status]
        for rid in t.get("requirements", []):
            if rid not in reqs:
                errors.append(f"{tid}: requirement {rid} is not in the SRS")
            elif rid not in verified:
                errors.append(f"{tid}: requirement {rid} is not verified")
        for cid in t.get("controls", []):
            if cid not in controls:
                errors.append(f"{tid}: risk control {cid} is not in the risk file")
        if status == "mitigated" and not t.get("requirements"):
            errors.append(f"{tid}: mitigated, so it names the requirements that mitigate it")
        if status == "environment" and not any(controls.get(c) == "information" for c in t.get("controls", [])):
            errors.append(f"{tid}: relies on the environment, so it names the information control that says so")
        if status in ("accepted", "not_applicable") and not t.get("note", "").strip():
            errors.append(f"{tid}: {status}, so its note gives the reason")
        # [/snippet:status]
    return errors


def main(root):
    doc = json.loads((root / THREATS).read_text())
    reqs, evidence, _ = parse_srs((root / SRS).read_text())
    verified = {r for r, _, _ in scan(root)} | set(evidence)
    risk = json.loads((root / RISK).read_text())
    controls = {c["id"]: c.get("type") for h in risk["hazards"] for c in h["controls"]}
    errors = check_diagram(doc, (root / DFD).read_text())
    errors += check_coverage(doc)
    errors += check_threats(doc, reqs, verified, controls)
    for e in errors:
        print(e)
    counts = {}
    for t in doc["threats"]:
        counts[t.get("status")] = counts.get(t.get("status"), 0) + 1
    summary = ", ".join(f"{n} {s}" for s, n in sorted(counts.items(), key=lambda x: -x[1]))
    print(f"threat model: {len(doc['elements'])} elements, {len(doc['threats'])} threats ({summary}), "
          + ("ok" if not errors else f"{len(errors)} problem(s)"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(pathlib.Path(sys.argv[1]).resolve()))
