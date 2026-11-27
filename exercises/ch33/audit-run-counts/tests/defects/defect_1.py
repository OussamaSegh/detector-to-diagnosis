# SPDX-License-Identifier: MIT
"""The end-to-end run's count checks: every single the simulator recorded reaches the
sorter's report, and the sorter's report accounts for every single it received. A count that
does not add up is a lost or invented event, and the run's verdict fails."""


def recorded_singles(generated_ps, end_ps):
    """How many of the simulator's generated singles (their times, in order) the run
    recorded, for a run that ends at end_ps."""
    # The simulator stops at the first single at or after the end, and keeps it for the next
    # call: it was generated, not recorded.
    return sum(1 for t in generated_ps if t < end_ps)


def partition_problems(c):
    """The problems of the sorter's partition of its singles; c is its report (a dict of
    counters). An empty list if every single is accounted for exactly once."""
    accounted = (c["energy_rejected"] + c["alone"] + 2 * c["pairs"] + c["in_multiples"])
    if accounted != c["singles_in"]:
        return [f"singles in {c['singles_in']} != accounted {accounted}"]
    return []
