# SPDX-License-Identifier: MIT
"""Exercise 34.4: hotspots from the history, the files with the highest product of commits and
code lines.

The input is the text of `git log --numstat --format='commit %H %as'`, newest commit first: a line
`commit <hash> <YYYY-MM-DD>`, then one line per file, `added<TAB>deleted<TAB>path` (`-` for both
counts of a binary file). A renamed path is written `old => new`, or with the common part outside
braces, `src/{old => new}/a.cpp`; either side of the braces may be empty.

This starter runs and gives plausible numbers. TODO: make the tests pass.
"""


def rename(path):
    """(old, new) for a path as numstat writes it; (path, path) when it is not a rename."""
    return path, path


def commits(text):
    """[(hash, date, [path, ...])], newest first, as the log gives them."""
    out = []
    for line in text.splitlines():
        if line.startswith("commit "):
            _, h, date = line.split()
            out.append((h, date, []))
        elif line.strip():
            out[-1][2].append(line.split("\t")[-1])
    return out


def hotspots(text, sizes, since="0000-00-00", mass=20):
    """Returns (ranking, mass_commits): [(path, commits, lines, score)], highest score first."""
    count = {}
    for h, date, paths in commits(text):
        for p in paths:
            count[p] = count.get(p, 0) + 1
    ranking = [(path, count.get(path, 0), lines, count.get(path, 0) * lines)
               for path, lines in sizes.items()]
    ranking.sort(key=lambda r: -r[3])
    return ranking, []
