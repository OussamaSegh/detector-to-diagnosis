# SPDX-License-Identifier: MIT
"""Exercise 17.1: the core of tools/check_threats.py for a proposed feature.

A threat model is {"applies": {kind: letters}, "elements": [...], "threats": [...]}, as in
docs/regulatory/security/threats.json. Statuses: mitigated (names requirements), environment
(states the assumption it relies on), accepted and not_applicable (a note says why).
"""
import json
import re

NODE = re.compile(r"^\s*([a-z_][a-z0-9_]*)\s*\[", re.M)
EDGE = re.compile(r"^\s*([a-z_][a-z0-9_]*)\s*->\s*([a-z_][a-z0-9_]*)", re.M)
STATUSES = {"mitigated", "environment", "accepted", "not_applicable"}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def requirement_ids(text):
    return {line.split()[0] for line in text.splitlines() if line.strip() and not line.startswith("#")}


def check_diagram(doc, dot):
    errors = []
    nodes = set(NODE.findall(dot)) - {"graph", "node", "edge"}
    edges = set(EDGE.findall(dot))
    for e in doc["elements"]:
        if e["kind"] == "flow":
            if (e.get("from"), e.get("to")) not in edges:
                errors.append(f"{e['id']}: no edge {e.get('from')} -> {e.get('to')} in the diagram")
        elif e["id"] not in nodes:
            errors.append(f"{e['id']}: not a node of the diagram")
    return errors


# [snippet:coverage]
def check_coverage(doc):
    """Every STRIDE category that applies to an element's kind has a threat."""
    # TODO: for each element, every letter of doc["applies"][kind] needs a threat.
    return []
# [/snippet:coverage]


def check_threats(doc, requirements):
    errors = []
    kinds = {e["id"]: e["kind"] for e in doc["elements"]}
    seen = set()
    for t in doc["threats"]:
        tid = t.get("id", "?")
        if tid in seen:
            errors.append(f"{tid}: defined twice")
        seen.add(tid)
        kind = kinds.get(t.get("element"))
        if kind is None:
            errors.append(f"{tid}: unknown element {t.get('element')}")
            continue
        if t.get("stride") not in doc["applies"][kind]:
            errors.append(f"{tid}: {t.get('stride')} does not apply to a {kind}")
        status = t.get("status")
        if status not in STATUSES:
            errors.append(f"{tid}: unknown status {status}")
            continue
        # TODO: requirements must be proposed ones; a mitigated threat names some; an environment
        # threat states its assumption; an accepted or not_applicable threat has a note.
    return errors


def check(doc, dot, requirements):
    return check_diagram(doc, dot) + check_coverage(doc) + check_threats(doc, requirements)
