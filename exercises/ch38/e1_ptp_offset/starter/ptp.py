# SPDX-License-Identifier: MIT
"""Exercise 38.1: a clock's offset from four time stamps (starter)."""


def offset_and_delay(t1, t2, t3, t4):
    """(offset, delay) of the slave's clock from one exchange: the master sends Sync at t1 (master
    time), the slave receives it at t2 (slave time), sends Delay_Req at t3 (slave time), and the
    master receives it at t4 (master time). offset = slave time - master time."""
    return t2 - t1, 0.0


def estimate(exchanges):
    """The offset from many exchanges [(t1, t2, t3, t4), ...] whose delays are the path's own plus
    queueing in switches, which only ever adds."""
    offsets = [offset_and_delay(*e)[0] for e in exchanges]
    return sum(offsets) / len(offsets)
