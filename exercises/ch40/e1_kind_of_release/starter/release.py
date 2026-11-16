# SPDX-License-Identifier: MIT
"""Exercise 40.1: the kind of release a change needs (starter).

TODO: the starter calls every change that fixes a problem report a patch, whatever else it
does, and its versions do not reset the lower numbers. See README.md."""
import re

KINDS = ("patch", "minor", "major")


def kind(change):
    """The smallest release that may carry `change` (see README.md)."""
    if change.get("fixes_report") or change.get("soup_update") or change.get("documentation"):
        return "patch"
    if change.get("breaks_clients"):
        return "major"
    return "minor"


def combined(changes):
    """The kind of one release that carries every change."""
    return kind(changes[0])


def next_version(current, release_kind):
    """The version after `current` for a release of `release_kind`."""
    x, y, z = (int(g) for g in re.findall(r"\d+", current)[:3])
    if release_kind == "patch":
        return f"{x}.{y}.{z + 1}"
    if release_kind == "minor":
        return f"{x}.{y + 1}.{z}"
    return f"{x + 1}.{y}.{z}"
