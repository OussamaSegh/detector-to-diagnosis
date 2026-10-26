# SPDX-License-Identifier: MIT
"""Exercise 21.5: find the commit that broke a test with `git bisect run` (solution).

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
SKIP = 125


# [snippet:check]
def check(workdir="."):
    """The exit status for git bisect run, for the commit checked out in workdir."""
    # First: can this commit be tested at all? A commit that does not build (here: import) says
    # nothing about the defect, so it is skipped, never called bad.
    # -B: no .pyc files. Two versions of app.py with the same size checked out within the same
    # second look alike to Python's cache check, and a stale .pyc would answer for the wrong commit.
    built = subprocess.run([sys.executable, "-B", "-c", "import app"], cwd=workdir, capture_output=True)
    if built.returncode != 0:
        return SKIP
    p = subprocess.run([sys.executable, "-B", "-c", "import app, sys; sys.exit(0 if app.answer() == 42 else 1)"],
                       cwd=workdir, capture_output=True)
    if p.returncode not in (0, 1):
        return SKIP  # the test itself crashed: not a verdict on the answer
    return p.returncode
# [/snippet:check]


def first_bad(repo, good, bad):
    """Runs git bisect between good and bad in repo and returns the list of candidate commits
    (full SHA-1): one commit if bisect found it, several if skipped commits leave it open."""
    def git(*args):
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)

    git("bisect", "reset")
    try:
        steps = [git("bisect", "start", bad, good), git("bisect", "run", sys.executable, str(CHECK))]
        # The bisection log, not the messages of `bisect run`: their wording changes between git
        # versions (2.43 and 2.55 differ), the log's comment lines are the record bisect keeps.
        steps.append(git("bisect", "log"))
        log = steps[-1].stdout
    finally:
        git("bisect", "reset")
    m = re.search(r"^# first bad commit: \[([0-9a-f]{40})\]", log, re.M)
    if m:
        return [m.group(1)]
    found = re.findall(r"^# possible first bad commit: \[([0-9a-f]{40})\]", log, re.M)
    if not found:
        # No answer is a failure to report, not an empty list a caller could read as "no defect".
        detail = "\n".join(f"$ {' '.join(s.args[3:])} -> {s.returncode}\n{s.stdout}{s.stderr}" for s in steps)
        raise RuntimeError(f"git bisect gave no result:\n{detail}")
    return found

if __name__ == "__main__":
    sys.exit(check())
