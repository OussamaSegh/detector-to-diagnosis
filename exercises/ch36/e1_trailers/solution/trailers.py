# SPDX-License-Identifier: MIT
"""Exercise 36.1: the trailers of a commit message, as git finds them (solution)."""
import re

LINE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9-]*)\s*:\s?(.*)$")


def trailers(message):
    """[(key, value)] of a commit message: its last paragraph, if every line in it is a trailer
    or a continuation, and if it is not the subject's paragraph."""
    lines = message.split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    start = len(lines)
    while start > 0 and lines[start - 1].strip():
        start -= 1
    if not any(not line.strip() for line in lines[:start]):
        return []  # no blank line before the block: it is the subject's paragraph
    found = []
    for line in lines[start:]:
        if line[:1].isspace() and found:
            key, val = found[-1]
            found[-1] = (key, f"{val} {line.strip()}")
        elif m := LINE.match(line):
            found.append((m.group(1), m.group(2).strip()))
        else:
            return []  # one line of prose and the paragraph is not a trailer block
    return found


def value(message, key):
    """The values of every trailer with this key, compared without regard to case."""
    return [v for k, v in trailers(message) if k.lower() == key.lower()]
