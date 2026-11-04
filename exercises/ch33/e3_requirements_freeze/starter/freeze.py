# SPDX-License-Identifier: MIT
"""Exercise 33.3: the SRS against its frozen baseline."""
import hashlib
import re

ROW = re.compile(r"^\|\s*(SRS-[A-Z]+-\d{3})\s*\|(.*)\|\s*$")
ID = re.compile(r"SRS-[A-Z]+-\d{3}")


def digests(srs_text):
    """{id: digest} of every requirement row: its text, item and method."""
    out = {}
    for line in srs_text.splitlines():
        m = ROW.match(line)
        if m:
            out[m.group(1)] = hashlib.sha256(m.group(2).encode()).hexdigest()[:16]
    return out


def differences(baseline, current):
    """[(id, how)], how in added, changed, removed, sorted by id."""
    out = [(r, "added") for r in current if r not in baseline]
    out += [(r, "changed") for r in current if r in baseline and current[r] != baseline[r]]
    return sorted(out)


def unexplained(baseline, srs_text, change_requests):
    """[(id, how)] of the differences that no approved or implemented request names."""
    named = set()
    for cr in change_requests:
        named.update(ID.findall(cr["text"]))
    return [(r, how) for r, how in differences(baseline, digests(srs_text)) if r not in named]
