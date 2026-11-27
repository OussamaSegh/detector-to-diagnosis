# SPDX-License-Identifier: MIT
"""What the daily QC report reads from a run's metadata (the first list-mode file's JSON).

The report is run by a technologist every morning. A run it cannot use is an error with a
reason, `error: ...` and status 2; a Python traceback is a defect, because the person who
reads it cannot act on it."""
from collections import namedtuple

Metadata = namedtuple("Metadata", "crystals delayed_window_ps")
DEFAULT_DELAYED_WINDOW_PS = 100_000


class FormatError(Exception):
    """The metadata cannot be used; the message says why."""


def read_metadata(meta):
    """The Metadata of a run, from its parsed JSON object `meta`, or FormatError."""
    try:
        crystals = int(meta["scanner"]["crystals"])
    except KeyError as e:
        raise FormatError(f"the metadata has no {e.args[0]}") from None
    window = int(meta.get("records", {}).get("delayed_window_ps", DEFAULT_DELAYED_WINDOW_PS))
    if crystals <= 0:
        raise FormatError(f"scanner.crystals is {crystals}, not a positive number")
    if window <= 0:
        raise FormatError(f"records.delayed_window_ps is {window}, not a positive number")
    return Metadata(crystals, window)
