# SPDX-License-Identifier: MIT
"""The guard an agent's shell commands pass before they run: it refuses a git push that would
change published history or reach a branch the session does not own (SDP section 5)."""
import re
import shlex

SEPARATORS = re.compile(r"\s*(?:&&|\|\||;|\||\n)\s*")


def words(segment):
    try:
        return shlex.split(segment)
    except ValueError:
        return segment.split()


def refusals(command, own_branch):
    """The reasons to refuse `command` (a shell command line), an empty list to allow it."""
    raise NotImplementedError
