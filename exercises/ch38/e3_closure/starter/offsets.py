# SPDX-License-Identifier: MIT
"""Exercise 38.3: block clock offsets from the shifts of pairs (starter)."""
from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass
class Offsets:
    offset: list = field(default_factory=list)    # per block; 0 if unobserved
    sigma: list = field(default_factory=list)     # per block; 0 if unobserved
    observed: list = field(default_factory=list)  # in a group of two or more blocks
    groups: int = 0
    chi2: float = 0.0
    dof: int = 0


def solve(n, pairs):
    """pairs: [(a, b, shift, variance)], shift = o_b - o_a measured with that variance."""
    out = Offsets([0.0] * n, [0.0] * n, [False] * n)
    edges = defaultdict(list)
    for a, b, s, _ in pairs:
        edges[a].append((b, s))
        edges[b].append((a, -s))
    seen = set()
    for start in range(n):
        if start in seen or not edges[start]:
            continue
        # Walk a spanning tree from the first block of the group, which is put at zero.
        out.groups += 1
        queue = deque([start])
        seen.add(start)
        while queue:
            a = queue.popleft()
            out.observed[a] = True
            for b, s in edges[a]:
                if b not in seen:
                    seen.add(b)
                    out.offset[b] = out.offset[a] + s
                    queue.append(b)
    return out
