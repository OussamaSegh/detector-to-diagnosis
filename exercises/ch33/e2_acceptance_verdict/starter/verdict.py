# SPDX-License-Identifier: MIT
"""Exercise 33.2: the verdict of one acceptance criterion from its evidence file."""
import json
import pathlib


def verdict(criterion, out, candidate):
    """(verdict, what was found): verdict in PASS, FAIL, MISSING, STALE."""
    path = pathlib.Path(out) / criterion["evidence"]
    evidence = json.loads(path.read_text())
    value = evidence["value"]
    if criterion["at_least"]:
        ok = not value < criterion["limit"]
    else:
        ok = not value > criterion["limit"]
    return ("PASS" if ok else "FAIL"), f"{value}"


def accepted(verdicts):
    """True when the candidate is accepted."""
    return "FAIL" not in verdicts
