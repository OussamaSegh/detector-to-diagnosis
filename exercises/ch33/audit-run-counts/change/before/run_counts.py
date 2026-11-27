# SPDX-License-Identifier: MIT
"""The end-to-end run's count checks: every single the simulator recorded reaches the
sorter's report, and the sorter's report accounts for every single it received. A count that
does not add up is a lost or invented event, and the run's verdict fails."""


def recorded_singles(generated_ps, end_ps):
    """How many of the simulator's generated singles (their times, in order) the run
    recorded, for a run that ends at end_ps."""
    raise NotImplementedError


def partition_problems(c):
    """The problems of the sorter's partition of its singles; c is its report (a dict of
    counters). An empty list if every single is accounted for exactly once."""
    raise NotImplementedError
