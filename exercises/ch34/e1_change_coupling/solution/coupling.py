# SPDX-License-Identifier: MIT
"""Exercise 34.1: the pairs of files that change in the same commits."""
import collections
import itertools


def commits(log):
    """[[files of one commit], ...] from `git log --name-only --format=@%H`."""
    out = []
    for line in log.splitlines():
        if line.startswith("@"):
            out.append([])
        elif line.strip() and out:
            out[-1].append(line.strip())
    return out


def coupling(log, min_shared=2, max_files=20):
    """[(a, b, shared, degree)], a < b, sorted by shared and degree descending, then a and b."""
    changes = collections.Counter()
    shared = collections.Counter()
    for files in commits(log):
        files = sorted(set(files))
        if len(files) > max_files:
            continue  # a mass change: every pair of its files would look coupled
        changes.update(files)
        for pair in itertools.combinations(files, 2):
            shared[pair] += 1
    out = [(a, b, n, n / min(changes[a], changes[b]))
           for (a, b), n in shared.items() if n >= min_shared]
    return sorted(out, key=lambda r: (-r[2], -r[3], r[0], r[1]))
