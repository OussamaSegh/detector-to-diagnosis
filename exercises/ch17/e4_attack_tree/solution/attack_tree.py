# SPDX-License-Identifier: MIT
"""Exercise 17.4: what an attack tree says once its leaves are marked.

A tree is JSON: an inner node {"id", "label", "op": "AND"|"OR", "children": [...]}, a leaf
{"id", "label", "blocked_by": [...]}. A leaf is blocked if any entry of blocked_by holds: an
entry "SRS-..." is a requirement, which holds if it is in `verified`; an entry "ENV:..." is an
assumption about the site, which holds if `assume_environment` is true. An attack is a set of
open leaves that together reach the root.
"""
import itertools
import json


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def leaf_open(leaf, verified, assume_environment):
    for b in leaf.get("blocked_by", []):
        if b.startswith("ENV:") and assume_environment:
            return False
        if not b.startswith("ENV:") and b in verified:
            return False
    return True


def minimize(sets):
    """Removes every set that contains another one: those attacks need more than necessary."""
    unique = sorted(set(sets), key=lambda s: (len(s), sorted(s)))
    out = []
    for s in unique:
        if not any(o <= s for o in out):
            out.append(s)
    return out


# [snippet:attacks]
def attacks(node, verified=frozenset(), assume_environment=True):
    """The minimal sets of open leaves that reach `node`, as a list of frozensets."""
    if "children" not in node:
        return [frozenset({node["id"]})] if leaf_open(node, verified, assume_environment) else []
    parts = [attacks(c, verified, assume_environment) for c in node["children"]]
    if node["op"] == "OR":
        return minimize(s for p in parts for s in p)
    if node["op"] == "AND":
        if any(not p for p in parts):
            return []  # one child cannot be reached, so neither can this node
        return minimize(frozenset().union(*combo) for combo in itertools.product(*parts))
    raise ValueError(f"{node['id']}: op must be AND or OR")
# [/snippet:attacks]


def requirements(node):
    """Every requirement that blocks a leaf of the tree."""
    if "children" not in node:
        return {b for b in node.get("blocked_by", []) if not b.startswith("ENV:")}
    return set().union(*(requirements(c) for c in node["children"]))


def critical(tree, verified, assume_environment=True):
    """The requirements whose failure alone opens a new attack on the root."""
    base = set(attacks(tree, verified, assume_environment))
    return sorted(r for r in requirements(tree)
                  if set(attacks(tree, verified - {r}, assume_environment)) - base)
