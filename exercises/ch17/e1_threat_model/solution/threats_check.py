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
    errors = []
    for e in doc["elements"]:
        done = {t["stride"] for t in doc["threats"] if t["element"] == e["id"]}
        for s in doc["applies"][e["kind"]]:
            if s not in done:
                errors.append(f"{e['id']}: no threat of category {s}")
    return errors
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
        for r in t.get("requirements", []):
            if r not in requirements:
                errors.append(f"{tid}: {r} is not a proposed requirement")
        if status == "mitigated" and not t.get("requirements"):
            errors.append(f"{tid}: mitigated by which requirements?")
        if status == "environment" and not t.get("assumption", "").strip():
            errors.append(f"{tid}: relies on the environment, so it states the assumption")
        if status in ("accepted", "not_applicable") and not t.get("note", "").strip():
            errors.append(f"{tid}: {status}, so a note says why")
    return errors


def check(doc, dot, requirements):
    return check_diagram(doc, dot) + check_coverage(doc) + check_threats(doc, requirements)
