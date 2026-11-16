# SPDX-License-Identifier: MIT
"""Exercise 39.3: block clock offsets from a point source (solution)."""
import math

C_MM_PER_PS = 0.299792458


def _solve(m, r):
    """x with m x = r, by Gauss-Jordan elimination with partial pivoting (m small and regular)."""
    n = len(r)
    a = [row[:] + [r[i]] for i, row in enumerate(m)]
    for c in range(n):
        p = max(range(c, n), key=lambda i: abs(a[i][c]))
        a[c], a[p] = a[p], a[c]
        d = a[c][c]
        a[c] = [x / d for x in a[c]]
        for i in range(n):
            if i != c and a[i][c] != 0.0:
                f = a[i][c]
                a[i] = [x - f * y for x, y in zip(a[i], a[c])]
    return [a[i][n] for i in range(n)]


def _groups(lap, index):
    """The connected groups of the observed blocks, through the pairs that have events."""
    left = set(index)
    out = []
    while left:
        stack = [min(left)]
        group = set(stack)
        while stack:
            i = stack.pop()
            for j in index:
                if j not in group and lap[i][j] != 0.0:
                    group.add(j)
                    stack.append(j)
        out.append(sorted(group))
        left -= group
    return out


def block_offsets(events, source, blocks):
    """Offsets (ps) of each block's clock, mean zero over the blocks with events; None for the
    others. events: [(a, b, block_a, block_b, t_a_ps, t_b_ps), ...].

    For each event the geometry predicts t_a - t_b = (|s - a| - |s - b|) / c; the rest is
    o_a - o_b plus noise. Least squares over every event: the normal equations L o = r have the
    graph Laplacian of the block pairs, singular along the common constant; adding 1/n to every
    entry of the observed blocks fixes their mean at zero (as in Exercise 38.3).

    The events must connect the observed blocks into one group, or the offset of one group against
    another is not measured at all: a point source at the center pairs each block only with the
    one opposite. That is a ValueError, not an answer."""
    lap = [[0.0] * blocks for _ in range(blocks)]
    rhs = [0.0] * blocks
    seen = [False] * blocks
    for a, b, ba, bb, ta, tb in events:
        if ba == bb:
            continue  # both singles in one block: their offsets cancel
        expected = (math.dist(source, a) - math.dist(source, b)) / C_MM_PER_PS
        residual = (ta - tb) - expected        # o_a - o_b + noise
        lap[ba][ba] += 1.0
        lap[bb][bb] += 1.0
        lap[ba][bb] -= 1.0
        lap[bb][ba] -= 1.0
        rhs[ba] += residual
        rhs[bb] -= residual
        seen[ba] = seen[bb] = True
    index = [k for k in range(blocks) if seen[k]]
    if not index:
        return [None] * blocks
    groups = _groups(lap, index)
    if len(groups) > 1:
        raise ValueError(f"the events connect the blocks in {len(groups)} groups, {groups}: "
                         "their offsets against each other are not measured")
    n = len(index)
    m = [[lap[i][j] + 1.0 / n for j in index] for i in index]
    x = _solve(m, [rhs[i] for i in index])
    out = [None] * blocks
    for k, i in enumerate(index):
        out[i] = x[k]
    return out
