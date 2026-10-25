# SPDX-License-Identifier: MIT
"""Exercise 17.4: what an attack tree says once its leaves are marked.

A tree is JSON: an inner node {"id", "label", "op": "AND"|"OR", "children": [...]}, a leaf
{"id", "label", "blocked_by": [...]}. A leaf is blocked if any entry of blocked_by holds: an
entry "SRS-..." is a requirement, which holds if it is in `verified`; an entry "ENV:..." is an
assumption about the site, which holds if `assume_environment` is true. An attack is a set of
open leaves that together reach the root.
"""
import json


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def leaf_open(leaf, verified, assume_environment):
    # TODO: a leaf is open unless one of its blockers holds.
    raise NotImplementedError


def minimize(sets):
    """Removes every set that contains another one: those attacks need more than necessary."""
    # TODO
    raise NotImplementedError


def attacks(node, verified=frozenset(), assume_environment=True):
    """The minimal sets of open leaves that reach `node`, as a list of frozensets."""
    # TODO: a leaf gives itself if open; OR takes the attacks of any child; AND combines one
    # attack of every child (itertools.product); then minimize.
    raise NotImplementedError


def requirements(node):
    """Every requirement that blocks a leaf of the tree."""
    if "children" not in node:
        return {b for b in node.get("blocked_by", []) if not b.startswith("ENV:")}
    return set().union(*(requirements(c) for c in node["children"]))


def critical(tree, verified, assume_environment=True):
    """The requirements whose failure alone opens a new attack on the root."""
    # TODO: remove one verified requirement at a time and compare the attacks.
    raise NotImplementedError
