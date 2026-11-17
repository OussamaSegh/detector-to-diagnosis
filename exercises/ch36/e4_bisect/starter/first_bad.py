# SPDX-License-Identifier: MIT
"""Exercise 36.4: a bisection that knows what an untestable commit leaves open.

`commits` is a first-parent history, oldest first. `good` is a commit known to pass and `bad` a
later one known to fail; neither is tested again. `test(commit)` returns "good", "bad" or "skip"
(the commit cannot be tested: it does not build, or the test cannot run on it), as the script of
`git bisect run` does with exit codes 0, 1 to 127 except 125, and 125.

This starter runs and finds a commit. TODO: make the tests pass.
"""


def bisect(commits, good, bad, test):
    """Returns (first_bad, candidates, tested)."""
    lo, hi = commits.index(good), commits.index(bad)
    tested = []
    while hi - lo > 1:
        i = (lo + hi) // 2
        verdict = test(commits[i])
        tested.append(commits[i])
        if verdict == "bad":
            hi = i
        else:  # a commit that cannot be tested is taken as good
            lo = i
    return commits[hi], [commits[hi]], tested
