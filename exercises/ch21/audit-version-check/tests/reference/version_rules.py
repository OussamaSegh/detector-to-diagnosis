# SPDX-License-Identifier: MIT
"""The rules for the version in VERSION, which every program reports: the server's hello, its
crash report, the list-mode files' software field. A crash report is read against the code of
the version it names, so that version must say which code the build is."""
import re


def key(v):
    """'1.10.2' -> (1, 10, 2), so that versions sort as numbers."""
    return tuple(int(x) for x in v.split("."))


def problems(version, subject, released):
    """The problems of VERSION's text `version` in a commit whose subject is `subject`, given
    the versions that have a release record (`released`). An empty list if it follows the
    rules."""
    m = re.fullmatch(r"(\d+\.\d+\.\d+)(-dev)?", version)
    if not m:
        return [f"VERSION '{version}' is not X.Y.Z or X.Y.Z-dev"]
    number, dev = m.group(1), m.group(2)
    newest = max(released, key=key, default=None)
    if dev:
        if newest and key(number) <= key(newest):
            return [f"VERSION {version} is not later than the newest release, {newest}"]
        return []
    if subject.startswith(f"Release {number}"):
        return []
    if subject.startswith(f"Tag book-v{number} "):
        return []  # the commit after the release commit, which lists its tag
    return [f"VERSION says {number}, a release, but this commit is not its release commit"]
