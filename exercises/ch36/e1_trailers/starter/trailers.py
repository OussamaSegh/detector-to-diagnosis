# SPDX-License-Identifier: MIT
"""Exercise 36.1: the trailers of a commit message (starter)."""
import re

LINE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9-]*):\s?(.*)$")


def trailers(message):
    """[(key, value)] of a commit message."""
    return [(m.group(1), m.group(2).strip()) for line in message.split("\n")
            if (m := LINE.match(line))]


def value(message, key):
    """The values of every trailer with this key."""
    return [v for k, v in trailers(message) if k == key]
