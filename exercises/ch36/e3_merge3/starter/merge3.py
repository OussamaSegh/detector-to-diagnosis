# SPDX-License-Identifier: MIT
"""Exercise 36.3: a three-way merge of lines (starter)."""


def merge3(base, ours, theirs, labels=("ours", "theirs")):
    """(lines, conflicts), line by line: at each index, the side that changed wins."""
    out, conflicts = [], 0
    for n in range(max(len(base), len(ours), len(theirs))):
        o = base[n] if n < len(base) else None
        x = ours[n] if n < len(ours) else None
        y = theirs[n] if n < len(theirs) else None
        if x == o:
            line = y
        elif y == o or x == y:
            line = x
        else:
            conflicts += 1
            line = x
        if line is not None:
            out.append(line)
    return out, conflicts
