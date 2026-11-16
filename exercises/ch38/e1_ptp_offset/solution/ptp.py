# SPDX-License-Identifier: MIT
"""Exercise 38.1: a clock's offset from four time stamps (solution)."""


def offset_and_delay(t1, t2, t3, t4):
    """(offset, delay) of the slave's clock from one exchange: the master sends Sync at t1 (master
    time), the slave receives it at t2 (slave time), sends Delay_Req at t3 (slave time), and the
    master receives it at t4 (master time). offset = slave time - master time.

    t2 - t1 = delay + offset and t4 - t3 = delay - offset when the path takes as long both ways."""
    forward = t2 - t1
    backward = t4 - t3
    return (forward - backward) / 2.0, (forward + backward) / 2.0


def estimate(exchanges, keep=0.1):
    """The offset from many exchanges [(t1, t2, t3, t4), ...] whose delays are the path's own plus
    queueing in switches, which only ever adds.

    Queueing makes the two directions unequal, and the error of the offset is half the difference.
    The exchanges with the shortest round trip met the least queueing: average the offsets of the
    fastest `keep` of them (at least one)."""
    measured = sorted((offset_and_delay(*e)[1], offset_and_delay(*e)[0]) for e in exchanges)
    n = max(1, int(len(measured) * keep))
    return sum(o for _, o in measured[:n]) / n
