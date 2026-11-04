# Exercise 33.2 (M): An acceptance verdict that cannot be fooled

**Goal.** Give each criterion of an acceptance specification one verdict from the evidence of a
release candidate: PASS, FAIL, MISSING or STALE, and accept the candidate only when every
criterion passes. The rules are those of `tools/acceptance.py`, on a simpler evidence format.

**Time.** 2 hours.

**The evidence.** Each criterion names a JSON file in the evidence directory:

    {"commit": "392e4ae", "dirty": false, "value": 37.47}

`commit` is the commit the measurement ran on (any prefix of at least 7 characters), `dirty` is
true when the working tree had changes, and `value` is the number measured. A criterion is

    {"id": "ACC-01", "evidence": "pipeline.json", "limit": 20.0, "at_least": true}

and passes when `value >= limit` (`at_least` true) or `value <= limit` (false).

**Starter.** `starter/verdict.py` gives the right verdict for evidence that is present, readable,
fresh and meets its target. Everything else is wrong in a way that lets a candidate through.

**Acceptance** (`tests/test_verdict.py`):
- PASS and FAIL at, just above and just below each limit, in both directions.
- MISSING for a file that does not exist, that is not JSON, that has no `value`, whose value is
  not a number (a string, `null`, `true`) or is not finite (NaN, infinity). Missing evidence is
  never a pass, and never an exception.
- STALE for evidence of another commit or of a dirty tree; a short and a long form of the same
  commit match, in either order; a prefix shorter than 7 characters matches nothing.
- `accepted` is true only when there is at least one verdict and every verdict is PASS.

**Then, by hand.**
1. The starter accepts a candidate whose soak was never run. Which line does it, and why is
   "nothing failed" the wrong question for a release?
2. Why must STALE be checked before the target? Give an example where the order changes the
   verdict a reader sees.
3. `json.loads` accepts `NaN`. Write down what `nan >= 20.0` and `not (nan < 20.0)` give, and
   say which form of a comparison is safe for a limit.

**Hints.** `bool` is a subclass of `int` in Python. `math.isfinite`. Catch only the exceptions
that mean the evidence cannot be read; let a bug in your own code still raise.
