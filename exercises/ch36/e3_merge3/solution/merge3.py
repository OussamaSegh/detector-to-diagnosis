# SPDX-License-Identifier: MIT
"""Exercise 36.3: a three-way merge of lines with conflicts (solution)."""
import difflib


def matches(base, other):
    """{index in base: index in other} for the lines a diff keeps, in increasing order."""
    sm = difflib.SequenceMatcher(None, base, other, autojunk=False)
    return {i + n: j + n for i, j, size in sm.get_matching_blocks() for n in range(size)}


def merge3(base, ours, theirs, labels=("ours", "theirs")):
    """(lines, conflicts): the merge of two descendants of base, lists of lines with their ends.

    The lines of base that both sides keep are the stable points; between two of them, a side
    that did not change takes the other's version, two equal changes are one, and two different
    changes are a conflict, written between markers."""
    a, b = matches(base, ours), matches(base, theirs)
    stable = [i for i in range(len(base)) if i in a and i in b]
    out, conflicts = [], 0
    i = j = k = 0
    for s in stable + [None]:
        end = (len(base), len(ours), len(theirs)) if s is None else (s, a[s], b[s])
        o, x, y = base[i:end[0]], ours[j:end[1]], theirs[k:end[2]]
        if x == o:
            out += y
        elif y == o or x == y:
            out += x
        else:
            conflicts += 1
            out += [f"<<<<<<< {labels[0]}\n", *ensure_end(x), "=======\n", *ensure_end(y),
                    f">>>>>>> {labels[1]}\n"]
        if s is not None:
            out.append(base[s])
            i, j, k = s + 1, a[s] + 1, b[s] + 1
    return out, conflicts


def ensure_end(lines):
    """A side's last line without a newline still leaves the marker on a line of its own."""
    if lines and not lines[-1].endswith("\n"):
        return lines[:-1] + [lines[-1] + "\n"]
    return lines
