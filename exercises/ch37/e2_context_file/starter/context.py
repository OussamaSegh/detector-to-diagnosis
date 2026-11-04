# SPDX-License-Identifier: MIT
"""Exercise 37.2: check that a context file names paths that exist (starter)."""
import os
import re

SPAN = re.compile(r"`([^`\n]+)`")


def references(text, tops):
    return [(n, s) for n, line in enumerate(text.splitlines(), start=1)
            for s in SPAN.findall(line) if "/" in s]


def problems(text, root):
    return [(n, f"{p} does not exist") for n, p in references(text, set())
            if not os.path.exists(os.path.join(root, p))]
