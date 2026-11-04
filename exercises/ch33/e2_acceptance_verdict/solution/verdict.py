# SPDX-License-Identifier: MIT
"""Exercise 33.2: the verdict of one acceptance criterion from its evidence file."""
import json
import math
import pathlib

SHORTEST = 7  # a commit prefix shorter than this names nothing


def same_commit(a, b):
    """True when a and b name the same commit: one is a prefix of the other, both long enough."""
    return min(len(a), len(b)) >= SHORTEST and (a.startswith(b) or b.startswith(a))


def verdict(criterion, out, candidate):
    """(verdict, what was found): verdict in PASS, FAIL, MISSING, STALE."""
    path = pathlib.Path(out) / criterion["evidence"]
    try:
        evidence = json.loads(path.read_text())
    except FileNotFoundError:
        return "MISSING", f"{criterion['evidence']} does not exist"
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        return "MISSING", f"cannot read {criterion['evidence']}: {type(e).__name__}"
    if not isinstance(evidence, dict):
        return "MISSING", f"{criterion['evidence']} is not an object"
    commit, dirty = evidence.get("commit"), evidence.get("dirty")
    if not isinstance(commit, str) or not isinstance(dirty, bool):
        return "MISSING", "the evidence names no commit"
    if dirty or not same_commit(commit, candidate):
        return "STALE", f"made on {commit}{' with changes' if dirty else ''}"
    value = evidence.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return "MISSING", f"no finite value: {value!r}"
    limit = criterion["limit"]
    ok = value >= limit if criterion["at_least"] else value <= limit
    return ("PASS" if ok else "FAIL"), f"{value:g}"


def accepted(verdicts):
    """True when the candidate is accepted: at least one verdict, and every one PASS."""
    verdicts = list(verdicts)
    return bool(verdicts) and all(v == "PASS" for v in verdicts)
