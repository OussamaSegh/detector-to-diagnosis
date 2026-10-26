# SPDX-License-Identifier: MIT
"""Exercise 21.4: what went wrong first, from the status snapshots of a run (solution).

A snapshot is {"t_s": seconds, "dropped": n, "stages": {stage: {"processed": n, "queue": n}}}
for the stages source, decode, sort, pair, write, in pipeline order, as a monitoring script
polls them about once a second. "processed" counts from the start of the server.
"""
import statistics

STAGES = ("source", "decode", "sort", "pair", "write")


def rates(snapshots, stage):
    out = []
    for prev, cur in zip(snapshots, snapshots[1:]):
        dn = cur["stages"][stage]["processed"] - prev["stages"][stage]["processed"]
        dt = cur["t_s"] - prev["t_s"]
        if dn < 0 or dt <= 0:
            continue  # a restart (counters from zero) or a clock that went back: no rate
        out.append((cur["t_s"], dn / dt))
    return out


def onset(snapshots, stage, baseline_s=10.0, drop=0.5):
    r = rates(snapshots, stage)
    if not r:
        return None
    start = snapshots[0]["t_s"]
    base = [v for t, v in r if t - start <= baseline_s]
    if not base:
        return None
    normal = statistics.median(base)
    for t, v in r:
        if t - start > baseline_s and v < drop * normal:
            return t
    return None


def first_to_slow(snapshots):
    found = [(onset(snapshots, s), i, s) for i, s in enumerate(STAGES)]
    found = [(t, i, s) for t, i, s in found if t is not None]
    if not found:
        return None
    earliest = min(t for t, _, _ in found)
    # Same interval: the furthest downstream (highest index) is the cause.
    _, _, stage = max((i, t, s) for t, i, s in found if t == earliest)
    return stage, earliest


def loss_began(snapshots):
    for prev, cur in zip(snapshots, snapshots[1:]):
        if cur["dropped"] > prev["dropped"]:
            return cur["t_s"]
    return None
