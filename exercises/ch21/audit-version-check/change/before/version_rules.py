# SPDX-License-Identifier: MIT
"""The rules for the version in VERSION, which every program reports: the server's hello, its
crash report, the list-mode files' software field. A crash report is read against the code of
the version it names, so that version must say which code the build is."""


def key(v):
    """'1.10.2' -> (1, 10, 2), so that versions sort as numbers."""
    return tuple(int(x) for x in v.split("."))


def problems(version, subject, released):
    """The problems of VERSION's text `version` in a commit whose subject is `subject`, given
    the versions that have a release record (`released`). An empty list if it follows the
    rules."""
    raise NotImplementedError
