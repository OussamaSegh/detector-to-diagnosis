# SPDX-License-Identifier: MIT
"""Exercise 21.4: what went wrong first, from the status snapshots of a run.

A snapshot is {"t_s": seconds, "dropped": n, "stages": {stage: {"processed": n, "queue": n}}}
for the stages source, decode, sort, pair, write, in pipeline order, as a monitoring script
polls them about once a second. "processed" counts from the start of the server.
"""
STAGES = ("source", "decode", "sort", "pair", "write")


def rates(snapshots, stage):
    """[(t_s, items per second)] for each interval between consecutive snapshots, at the time of
    the later one. An interval in which the counter went down (the server restarted) has no rate:
    leave it out. Divide by the real time between the snapshots, not by 1."""
    raise NotImplementedError  # TODO


def onset(snapshots, stage, baseline_s=10.0, drop=0.5):
    """The first time after the baseline at which the stage's rate is below `drop` times its
    median rate during the first `baseline_s` seconds of the snapshots; None if never."""
    raise NotImplementedError  # TODO


def first_to_slow(snapshots):
    """(stage, t_s): the stage that slowed first, and when. If several slowed in the same
    interval, the one furthest downstream: a slow stage holds up the ones before it, never the
    ones after it, at once. None if no stage slowed."""
    raise NotImplementedError  # TODO


def loss_began(snapshots):
    """The time of the first snapshot whose "dropped" is higher than the one before; None if the
    source never dropped."""
    raise NotImplementedError  # TODO
