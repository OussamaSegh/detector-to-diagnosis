# SPDX-License-Identifier: MIT
"""Exercise 39.3: block clock offsets from a point source (starter)."""


def block_offsets(events, source, blocks):
    """Offsets (ps) of each block's clock, mean zero over the blocks with events; None for the
    others. events: [(a, b, block_a, block_b, t_a_ps, t_b_ps), ...]."""
    total = [0.0] * blocks
    count = [0] * blocks
    for _a, _b, ba, bb, ta, tb in events:
        total[ba] += ta - tb
        count[ba] += 1
        total[bb] -= ta - tb
        count[bb] += 1
    out = [total[k] / count[k] if count[k] else None for k in range(blocks)]
    seen = [o for o in out if o is not None]
    mean = sum(seen) / len(seen)
    return [None if o is None else o - mean for o in out]
