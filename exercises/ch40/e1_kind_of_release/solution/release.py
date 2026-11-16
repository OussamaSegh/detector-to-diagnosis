# SPDX-License-Identifier: MIT
"""Exercise 40.1: the kind of release a change needs (solution)."""
import re

KINDS = ("patch", "minor", "major")


def kind(change):
    """The smallest release that may carry `change`, a dict of booleans (missing keys are False):
    breaks_clients, new_requirement, changes_format, changes_api, new_soup, new_feature,
    fixes_report, soup_update, documentation. The maintenance plan's table, section 4: what
    breaks an existing client, configuration or file is major; any compatible addition is
    minor; a fix, a SOUP update in the same version line and a documentation correction are a
    patch, and only when nothing else in the change needs more."""
    if change.get("breaks_clients"):
        return "major"
    if any(change.get(k) for k in ("new_requirement", "changes_format", "changes_api",
                                   "new_soup", "new_feature")):
        return "minor"
    if any(change.get(k) for k in ("fixes_report", "soup_update", "documentation")):
        return "patch"
    raise ValueError("the change does nothing a release could carry")


def combined(changes):
    """The kind of one release that carries every change: the largest of their kinds."""
    if not changes:
        raise ValueError("no change")
    return max((kind(c) for c in changes), key=KINDS.index)


def next_version(current, release_kind):
    """The version after `current` (a released X.Y.Z) for a release of `release_kind`."""
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", current)
    if not m:
        raise ValueError(f"{current!r} is not a released version X.Y.Z")
    x, y, z = (int(g) for g in m.groups())
    if release_kind == "patch":
        return f"{x}.{y}.{z + 1}"
    if release_kind == "minor":
        return f"{x}.{y + 1}.0"
    if release_kind == "major":
        return f"{x + 1}.0.0"
    raise ValueError(f"unknown kind {release_kind!r}")
