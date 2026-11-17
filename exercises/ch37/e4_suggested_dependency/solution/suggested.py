# SPDX-License-Identifier: MIT
"""Exercise 37.4, a solution: check a dependency an assistant suggests before it is locked.

A suggestion is one requirement line, such as `pydicom==3.0.1`. It is compared with the lock file
(`name==version` lines, comments and `--hash` lines ignored) and with the approved packages of the
SOUP list. Names are compared as the package index compares them (PEP 503): case does not matter,
and runs of `-`, `_` and `.` are one `-`.
"""
import re

_LINE = re.compile(r"([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\s*(?:(==|>=|<=|~=|!=|>|<)\s*"
                   r"([A-Za-z0-9.*+!_-]+))?")


def normalize(name):
    """The name the package index uses for comparison (PEP 503)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse(line):
    """(name, operator, version) of one requirement line; operator and version are None for a bare
    name. Anything else raises ValueError."""
    m = _LINE.fullmatch(line.strip())
    if not m:
        raise ValueError(f"not a requirement: {line!r}")
    return m.group(1), m.group(2), m.group(3)


def locked(lock_text):
    """{normalized name: version} of the exact pins of a lock file."""
    out = {}
    for line in lock_text.splitlines():
        line = line.split("#", 1)[0].strip().rstrip("\\").strip()
        if not line or line.startswith("-"):
            continue
        name, op, version = parse(line)
        if op == "==":
            out[normalize(name)] = version
    return out


def distance(a, b):
    """Edits between a and b: insertions, deletions, substitutions and swaps of two neighbors
    (optimal string alignment)."""
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[len(a)][len(b)]


def _squash(name):
    """A name without separators and the usual decorations, for comparing look-alikes."""
    n = normalize(name).replace("-", "")
    for prefix in ("python", "py"):
        if n.startswith(prefix) and len(n) > len(prefix) + 2:
            n = n[len(prefix):]
    return n


def check(line, lock_text, approved):
    """The findings for one suggested requirement, in this order:
    'unpinned' unless it is name==version; 'not-approved' unless the SOUP list names it;
    'near:<approved>' for every approved package it could be mistaken for; 'already-locked' or
    'conflict:<locked version>' when the lock file pins it."""
    name, op, version = parse(line)
    key = normalize(name)
    approved = {normalize(a): a for a in approved}
    findings = []
    if op != "==" or "*" in (version or ""):
        findings.append("unpinned")
    if key not in approved:
        findings.append("not-approved")
        limit = 1 if len(key) < 5 else 2
        for a_key, a in sorted(approved.items()):
            if distance(key, a_key) <= limit or _squash(key) == _squash(a_key):
                findings.append(f"near:{a}")
    pins = locked(lock_text)
    if key in pins:
        findings.append("already-locked" if (op, version) == ("==", pins[key])
                        else f"conflict:{pins[key]}")
    return findings
