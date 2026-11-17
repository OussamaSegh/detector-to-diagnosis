# SPDX-License-Identifier: MIT
"""Exercise 34.4, a solution: hotspots from the history, the files with the highest product of
commits and code lines, without the commits that touch everything and with each file's history
followed through its renames.

The input is the text of `git log --numstat --format='commit %H %as'`, newest commit first: a line
`commit <hash> <YYYY-MM-DD>`, then one line per file, `added<TAB>deleted<TAB>path` (`-` for both
counts of a binary file). A renamed path is written `old => new`, or with the common part outside
braces, `src/{old => new}/a.cpp`; either side of the braces may be empty.
"""
import re

_BRACES = re.compile(r"^(.*)\{(.*) => (.*)\}(.*)$")


def _join(*parts):
    return "/".join(p for p in "".join(parts).split("/") if p)


def rename(path):
    """(old, new) for a path as numstat writes it; (path, path) when it is not a rename."""
    m = _BRACES.match(path)
    if m:
        head, old, new, tail = m.groups()
        return _join(head, old, tail), _join(head, new, tail)
    if " => " in path:
        old, new = path.split(" => ", 1)
        return old, new
    return path, path


def commits(text):
    """[(hash, date, [path, ...])], newest first, as the log gives them."""
    out = []
    for line in text.splitlines():
        if line.startswith("commit "):
            _, h, date = line.split()
            out.append((h, date, []))
        elif line.strip():
            if not out:
                raise ValueError(f"a file before any commit: {line!r}")
            added, deleted, path = line.split("\t", 2)
            out[-1][2].append(path)
    return out


def hotspots(text, sizes, since="0000-00-00", mass=20):
    """Returns (ranking, mass_commits). ranking: [(path, commits, lines, score)] for the files in
    `sizes` (the current code lines of each file that exists now), highest score first, then by
    path. A commit that touches more than `mass` files is left out of the counts and listed in
    mass_commits, newest first; so are commits older than `since` (left out, not listed)."""
    current = {}  # an old name -> the name the file has now

    def now(name):
        seen = set()
        while name in current and name not in seen:
            seen.add(name)
            name = current[name]
        return name

    count = {}
    left_out = []
    for h, date, paths in commits(text):
        names = []
        for p in paths:
            old, new = rename(p)
            target = now(new)
            if old != new:
                current[old] = target
            names.append(target)
        if date < since:
            continue
        if len(paths) > mass:
            left_out.append(h)
            continue
        for name in set(names):
            count[name] = count.get(name, 0) + 1
    ranking = [(path, count.get(path, 0), lines, count.get(path, 0) * lines)
               for path, lines in sizes.items()]
    ranking.sort(key=lambda r: (-r[3], r[0]))
    return ranking, left_out
