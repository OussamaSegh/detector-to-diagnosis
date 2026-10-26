# SPDX-License-Identifier: MIT
"""Exercise 21.5: find the commit that broke a test with `git bisect run`.

The repository's program is app.py; a commit is good if app.answer() returns 42. Some commits in
the history do not even import (a syntax error, a half-finished refactoring). git bisect run
reads the exit status of the check: 0 good, 1 to 127 bad except 125, which means "cannot test
this commit, skip it".
"""
import pathlib
import re
import subprocess
import sys

CHECK = pathlib.Path(__file__).resolve()


def check(workdir="."):
    """The exit status for git bisect run, for the commit checked out in workdir."""
    # TODO: this treats a commit that cannot be tested as bad. Bisect then blames the first
    # broken commit instead of the one that changed the answer.
    # -B: no .pyc files. Two versions of app.py with the same size checked out within the same
    # second look alike to Python's cache check, and a stale .pyc would answer for the wrong commit.
    p = subprocess.run([sys.executable, "-B", "-c", "import app, sys; sys.exit(0 if app.answer() == 42 else 1)"],
                       cwd=workdir, capture_output=True)
    return 0 if p.returncode == 0 else 1


def candidates(log):
    """The candidate commits (full SHA-1) that the text of `git bisect log` names: the first bad
    commit if bisect found it, the possible first bad commits if skipped commits leave it open.
    Even the log's comments changed: git 2.43 writes "first bad commit", git 2.55 quotes the term,
    "first 'bad' commit" (bisect lets you rename good and bad). Both are accepted."""
    m = re.search(r"^# first '?bad'? commit: \[([0-9a-f]{40})\]", log, re.M)
    if m:
        return [m.group(1)]
    # TODO: when skipped commits leave it open, the log lists the candidates on lines
    # "# possible first bad commit: [SHA-1] subject". Return them.
    return []


def first_bad(repo, good, bad):
    """Runs git bisect between good and bad in repo and returns the list of candidate commits
    (full SHA-1): one commit if bisect found it, several if skipped commits leave it open."""
    def git(*args):
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)

    git("bisect", "reset")
    try:
        git("bisect", "start", bad, good)
        git("bisect", "run", sys.executable, str(CHECK))
        # The bisection log, not the messages of `bisect run`, which are written for people.
        log = git("bisect", "log").stdout
    finally:
        git("bisect", "reset")
    return candidates(log)

if __name__ == "__main__":
    sys.exit(check())
