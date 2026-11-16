# SPDX-License-Identifier: MIT
"""Exercise 40.3: which releases contain a defect (starter).

TODO: the starter follows first parents only and looks for the fix by its id, so it misses a
change merged from a branch and every cherry-pick. See README.md."""


def affected(commits, tags, introduced, fix):
    """The released versions that contain the defect (see README.md)."""
    out = []
    for version, tip in tags.items():
        history = []
        c = tip
        while c is not None:
            history.append(c)
            parents = commits[c]["parents"]
            c = parents[0] if parents else None
        if introduced in history and fix not in history:
            out.append(version)
    return sorted(out)
