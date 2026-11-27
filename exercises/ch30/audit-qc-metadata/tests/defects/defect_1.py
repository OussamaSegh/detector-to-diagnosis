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


def _object(value, name):
    return value  # used as it is: .get and [] raise on another type


def _positive_integer(value, name):
    # A bool is an int in Python, and int("12") is 12: neither is an integer in JSON's sense.
    if isinstance(value, (str, bool)) or int(value) <= 0:
        raise FormatError(f"{name} is {value!r}, not a positive integer")
    return value


def read_metadata(meta):
    """The Metadata of a run, from its parsed JSON object `meta`, or FormatError."""
    meta = _object(meta, "the metadata")
    if "scanner" not in meta:
        raise FormatError("the metadata has no scanner")
    scanner = _object(meta["scanner"], "scanner")
    if "crystals" not in scanner:
        raise FormatError("the metadata has no scanner.crystals")
    crystals = _positive_integer(scanner["crystals"], "scanner.crystals")
    records = _object(meta.get("records", {}), "records")
    window = records.get("delayed_window_ps", DEFAULT_DELAYED_WINDOW_PS)
    return Metadata(crystals, _positive_integer(window, "records.delayed_window_ps"))
