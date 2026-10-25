# SPDX-License-Identifier: MIT
"""Exercise 11.3: finding the first bottleneck from minidaq_latency reports.

minidaq_latency prints, after its latency table, one line per stage:

    stage            items in  busy %   out stalls      in idle      dropped
    decode            8389315     2.7            0       173873            0

busy % is the stage's summed batch service time over the wall time. A stage
that is busy all the time cannot keep up; a stage whose output queue is full
stalls (out stalls), and one with nothing to do idles (in idle). The first line
of the report gives the offered rate and what the source dropped.
"""
import re
from dataclasses import dataclass, field

# The replay source's busy % is its own work (clock reads, copies), not a
# limit of the pipeline it feeds: a real source is a network card.
NOT_A_LIMIT = ("source",)


@dataclass
class StageUse:
    items_in: int
    busy_pct: float
    out_stalls: int
    in_idle: int
    dropped: int


@dataclass
class Report:
    rate: float          # words (singles) per second offered
    delivered: int
    dropped: int         # by the source: the pipeline's input queue was full
    stages: dict = field(default_factory=dict)  # name -> StageUse, in report order


_HEAD = re.compile(r"^rate ([\d.e+]+) words/s.*delivered (\d+), dropped (\d+)", re.MULTILINE)
_STAGE = re.compile(r"^(\w[\w-]*)\s+(\d+)\s+([\d.]+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$", re.MULTILINE)


def parse_report(text):
    head = _HEAD.search(text)
    if head is None:
        raise ValueError("not a minidaq_latency report: no rate line")
    r = Report(rate=float(head.group(1)), delivered=int(head.group(2)), dropped=int(head.group(3)))
    # The latency table's lines do not match: all its numbers after the first
    # have decimals, and the utilization table's are integers but for busy %.
    # TODO: one line per stage.
    m = _STAGE.search(text)
    if m:
        r.stages[m.group(1)] = StageUse(int(m.group(2)), float(m.group(3)), int(m.group(4)), int(m.group(5)),
                                        int(m.group(6)))
    if not r.stages:
        raise ValueError("not a minidaq_latency report: no utilization table")
    return r


def busiest(report):
    """(name, busy %) of the busiest stage that can limit the pipeline."""
    # TODO: is every stage's busy % a limit?
    candidates = [(n, s.busy_pct) for n, s in report.stages.items()]
    return max(candidates, key=lambda c: c[1])


def saturated(report, busy_limit=90.0):
    """The stage that cannot keep up, or None: a stage at or above busy_limit,
    or, when the source dropped data, the busiest stage."""
    name, busy = busiest(report)
    # TODO: a source that drops data is a sign too.
    if busy >= busy_limit:
        return name
    return None


def capacity(reports, stage):
    """The rate at which `stage` would be 100% busy, from a sweep: busy % is
    proportional to the rate, busy = c * rate, fitted by least squares through
    the origin (a stage with no input does no work)."""
    # TODO: fit all the points, not only the last one.
    last = reports[-1]
    return 100.0 * last.rate / last.stages[stage].busy_pct


def first_bottleneck(reports):
    """(name, capacity) of the stage with the lowest fitted capacity."""
    names = [n for n in reports[0].stages if n not in NOT_A_LIMIT]
    caps = {n: capacity(reports, n) for n in names if any(r.stages[n].busy_pct > 0 for r in reports)}
    name = min(caps, key=caps.get)
    return name, caps[name]
