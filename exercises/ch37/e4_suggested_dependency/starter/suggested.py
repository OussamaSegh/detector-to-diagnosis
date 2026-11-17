# SPDX-License-Identifier: MIT
"""Exercise 37.4: check a dependency an assistant suggests before it is locked.

A suggestion is one requirement line, such as `pydicom==3.0.1`. It is compared with the lock file
(`name==version` lines, comments and `--hash` lines ignored) and with the approved packages of the
SOUP list. Names are compared as the package index compares them (PEP 503): case does not matter,
and runs of `-`, `_` and `.` are one `-`.

This starter runs and gives plausible findings. TODO: make the tests pass.
"""


def check(line, lock_text, approved):
    """The findings for one suggested requirement: 'unpinned', 'not-approved', 'near:<approved>',
    'already-locked' or 'conflict:<locked version>'."""
    name, _, version = line.strip().partition("=")
    version = version.lstrip("=<>~")
    findings = []
    if not version:
        findings.append("unpinned")
    if name not in approved:
        findings.append("not-approved")
    for lock_line in lock_text.splitlines():
        if lock_line.startswith(name + "=="):
            pinned = lock_line.split("==")[1].split()[0]
            findings.append("already-locked" if pinned == version else f"conflict:{pinned}")
    return findings
