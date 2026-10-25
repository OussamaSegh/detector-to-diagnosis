# SPDX-License-Identifier: MIT
"""Exercise 11.5: an end-to-end throughput budget for the acquisition chain.

Every stage of the chain has a load that grows with the activity A (Bq) and a
capacity in the same unit: the readout link carries singles, the sorter sorts
them, the disk stores coincidences. The budget answers two questions: which
stage saturates first as A rises, and at which activity a stage reaches its
capacity less a safety margin.
"""
import math
from dataclasses import dataclass
from typing import Callable

# Chapter 9: Ethernet, IPv4 and UDP overhead per datagram, in bytes of link time.
FRAME_OVERHEAD = 14 + 4 + 20 + 8   # Ethernet header and FCS, IPv4, UDP
WIRE_OVERHEAD = 8 + 12             # preamble with start delimiter, inter-frame gap
MDQ_HEADER = 16
WORD = 8


def link_singles_capacity(link_bits_per_s, words_per_packet, links=1):
    """Singles per second that fill `links` links of MDQ-R1 packets."""
    wire = FRAME_OVERHEAD + WIRE_OVERHEAD + MDQ_HEADER + WORD * words_per_packet
    return links * link_bits_per_s / 8.0 / (wire / words_per_packet)


@dataclass
class Stage:
    name: str
    load: Callable[[float], float]   # activity (Bq) -> load, in the stage's unit
    capacity: float                  # the load at which the stage is full


def utilization(stage, activity):
    return stage.load(activity) / stage.capacity


# [snippet:saturation]
def saturation_activity(stage, margin=0.0, hi=1e11):
    """The activity at which `stage` reaches (1 - margin) of its capacity.
    Loads grow with the activity, so bisection finds it; inf if not below hi."""
    target = 1.0 - margin
    if utilization(stage, hi) < target:
        return math.inf
    lo = 0.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if utilization(stage, mid) < target:
            lo = mid
        else:
            hi = mid
    return hi


def first_bottleneck(stages, margin=0.0):
    """(name, activity) of the stage that saturates at the lowest activity."""
    best = min(stages, key=lambda s: saturation_activity(s, margin))
    return best.name, saturation_activity(best, margin)
# [/snippet:saturation]
