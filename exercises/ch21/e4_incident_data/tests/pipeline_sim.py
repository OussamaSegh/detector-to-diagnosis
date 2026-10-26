# SPDX-License-Identifier: MIT
"""A one-second-step model of MiniDAQ's five stages, to make the status snapshots of an incident
(Exercise 21.4). Each second, each stage processes what it can from its input queue, limited by
its capacity and by the room in its output queue; the source offers `offered` items a second and
drops what does not fit. At `at_s`, one stage's capacity falls to `factor` of normal."""
import random

STAGES = ("source", "decode", "sort", "pair", "write")


def simulate(seconds=60, offered=1000, capacity=1500, queue_max=4000, slow=None, at_s=30, factor=0.3,
             seed=1, restart_at=None, missing=()):
    rng = random.Random(seed)
    processed = {s: 0 for s in STAGES}
    queue = {s: 0 for s in STAGES}  # the queue in front of each stage (source: unused)
    dropped = 0
    snapshots = []
    t = 0.0
    for sec in range(seconds):
        cap = {s: capacity for s in STAGES}
        if slow is not None and sec >= at_s:
            cap[slow] = int(capacity * factor)
        # From the last stage back, so that room freed downstream is used in the same second.
        room = {}
        for i in reversed(range(len(STAGES))):
            s = STAGES[i]
            out_room = queue_max - queue[STAGES[i + 1]] if i + 1 < len(STAGES) else float("inf")
            avail = offered + rng.randint(-20, 20) if i == 0 else queue[s]
            n = int(min(avail, cap[s], out_room))
            if i == 0:
                dropped += max(0, avail - n)
            else:
                queue[s] -= n
            if i + 1 < len(STAGES):
                queue[STAGES[i + 1]] += n
            processed[s] += n
            room[s] = out_room
        t += 1.0 + rng.uniform(-0.02, 0.02)  # the poller is not exact
        if restart_at is not None and sec == restart_at:
            processed = {s: 0 for s in STAGES}  # the server restarted: counters from zero
        if sec in missing:
            continue  # the poller missed this snapshot
        snapshots.append({"t_s": round(t, 3), "dropped": dropped,
                          "stages": {s: {"processed": processed[s], "queue": queue[s]} for s in STAGES}})
    return snapshots
