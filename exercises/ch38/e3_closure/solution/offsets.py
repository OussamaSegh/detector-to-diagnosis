# SPDX-License-Identifier: MIT
"""Exercise 38.3: block clock offsets from the shifts of pairs (solution)."""
from dataclasses import dataclass, field


@dataclass
class Offsets:
    offset: list = field(default_factory=list)    # per block; 0 if unobserved
    sigma: list = field(default_factory=list)     # per block; 0 if unobserved
    observed: list = field(default_factory=list)  # in a group of two or more blocks
    groups: int = 0
    chi2: float = 0.0
    dof: int = 0


def _groups(n, pairs):
    parent = list(range(n))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b, _, _ in pairs:
        parent[root(a)] = root(b)
    return [root(i) for i in range(n)]


def _inverse(m):
    """Gauss-Jordan inverse with partial pivoting of a small dense matrix."""
    n = len(m)
    a = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(m)]
    for c in range(n):
        p = max(range(c, n), key=lambda i: abs(a[i][c]))
        a[c], a[p] = a[p], a[c]
        d = a[c][c]
        a[c] = [x / d for x in a[c]]
        for i in range(n):
            if i != c and a[i][c] != 0.0:
                f = a[i][c]
                a[i] = [x - f * y for x, y in zip(a[i], a[c])]
    return [row[n:] for row in a]


def solve(n, pairs):
    """pairs: [(a, b, shift, variance)], shift = o_b - o_a measured with that variance.

    The weighted least squares solution: minimize the sum of (shift - (o_b - o_a))^2 / variance.
    Its normal equations L o = r have the graph's Laplacian, which is singular: every group of
    connected blocks can move together without changing a pair. Fix each group's mean at zero by
    adding J/size for the group (J all ones); the inverse of L + J/size, less J/size, is then the
    covariance of the offsets. Pairs that disagree with any set of block clocks show in chi2."""
    pairs = [p for p in pairs if p[3] > 0.0 and p[0] != p[1]]
    out = Offsets([0.0] * n, [0.0] * n, [False] * n)
    root = _groups(n, pairs)
    size = {}
    for r in root:
        size[r] = size.get(r, 0) + 1
    L = [[0.0] * n for _ in range(n)]
    r = [0.0] * n
    for a, b, s, v in pairs:
        w = 1.0 / v
        L[a][a] += w
        L[b][b] += w
        L[a][b] -= w
        L[b][a] -= w
        r[b] += w * s
        r[a] -= w * s
    M = [[L[i][j] + (1.0 / size[root[i]] if root[i] == root[j] else 0.0) for j in range(n)]
         for i in range(n)]
    inv = _inverse(M)
    observed = [size[root[i]] >= 2 for i in range(n)]
    for i in range(n):
        if observed[i]:
            out.offset[i] = sum(inv[i][j] * r[j] for j in range(n))
            out.sigma[i] = max(0.0, inv[i][i] - 1.0 / size[root[i]]) ** 0.5
    out.observed = observed
    out.groups = len({root[i] for i in range(n) if observed[i]})
    for a, b, s, v in pairs:
        out.chi2 += (s - (out.offset[b] - out.offset[a])) ** 2 / v
    unknowns = sum(observed) - out.groups
    out.dof = max(0, len(pairs) - unknowns)
    return out
