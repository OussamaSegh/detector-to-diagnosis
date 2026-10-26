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


def first_bad(repo, good, bad):
    """Runs git bisect between good and bad in repo and returns the list of candidate commits
    (full SHA-1): one commit if bisect found it, several if skipped commits leave it open."""
    def git(*args):
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)

    git("bisect", "reset")
    try:
        git("bisect", "start", bad, good)
        out = git("bisect", "run", sys.executable, str(CHECK)).stdout
    finally:
        git("bisect", "reset")
    m = re.search(r"^([0-9a-f]{40}) is the first bad commit", out, re.M)
    if m:
        return [m.group(1)]
    # TODO: when skipped commits leave it open, bisect lists the candidates after
    # "The first bad commit could be any of:". Return them.
    return []


if __name__ == "__main__":
    sys.exit(check())
