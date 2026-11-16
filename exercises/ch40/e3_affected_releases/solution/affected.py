# SPDX-License-Identifier: MIT
"""Exercise 40.3: which releases contain a defect (solution)."""
import re

PICKED = re.compile(r"\(cherry picked from commit (\w+)\)")


def ancestors(commits, start):
    """Every commit reachable from `start` through all parents, `start` included. Iterative: a
    history of thousands of commits would overflow a recursive walk."""
    seen = set()
    stack = [start]
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        if c not in commits:
            raise KeyError(f"unknown commit {c}")
        seen.add(c)
        stack.extend(commits[c]["parents"])
    return seen


def contains_fix(commits, history, fix):
    """True if the history holds the fix itself or a cherry-pick of it, which names it in its
    message as `git cherry-pick -x` writes it (a pick of a pick names the one it copied)."""
    copies = {fix}
    changed = True
    while changed:  # a pick of a pick: follow the chain to the original
        changed = False
        for c, info in commits.items():
            m = PICKED.search(info.get("message", ""))
            if c not in copies and m and m.group(1) in copies:
                copies.add(c)
                changed = True
    return bool(history & copies)


def affected(commits, tags, introduced, fix):
    """The released versions whose tag contains the change that introduced the defect and
    neither the fix nor a cherry-pick of it, sorted as version numbers. commits: {id:
    {"parents": [...], "message": str}}; tags: {version: commit id}."""
    out = []
    for version, tip in tags.items():
        history = ancestors(commits, tip)
        if introduced in history and not contains_fix(commits, history, fix):
            out.append(version)
    return sorted(out, key=lambda v: tuple(int(x) for x in v.split(".")))
