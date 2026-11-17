# SPDX-License-Identifier: MIT
"""Exercise 36.4, a solution: a bisection that knows what an untestable commit leaves open.

`commits` is a first-parent history, oldest first. `good` is a commit known to pass and `bad` a
later one known to fail; neither is tested again. `test(commit)` returns "good", "bad" or "skip"
(the commit cannot be tested: it does not build, or the test cannot run on it), as the script of
`git bisect run` does with exit codes 0, 1 to 127 except 125, and 125.
"""


def bisect(commits, good, bad, test):
    """Returns (first_bad, candidates, tested). first_bad is the first bad commit when the tests
    pin it down, else None; candidates are the commits it can still be, oldest first (one when it
    is pinned down, more when untestable commits are in the way); tested lists the commits tested,
    in order, each at most once."""
    index = {c: i for i, c in enumerate(commits)}
    if good not in index or bad not in index:
        raise ValueError("good and bad must both be in the history")
    lo, hi = index[good], index[bad]  # lo is good, hi is bad; the answer is in (lo, hi]
    if lo >= hi:
        raise ValueError(f"good {good} is not before bad {bad}")
    skipped = set()
    tested = []
    while True:
        open_ = [i for i in range(lo + 1, hi) if i not in skipped]
        if not open_:
            break
        middle = (lo + hi) / 2
        i = min(open_, key=lambda k: (abs(k - middle), k))  # nearest the middle, older on a tie
        verdict = test(commits[i])
        tested.append(commits[i])
        if verdict == "good":
            lo = i
        elif verdict == "bad":
            hi = i
        elif verdict == "skip":
            skipped.add(i)
        else:
            raise ValueError(f"test({commits[i]!r}) returned {verdict!r}, not good, bad or skip")
    candidates = [commits[i] for i in range(lo + 1, hi + 1)]
    return (candidates[0] if len(candidates) == 1 else None), candidates, tested
