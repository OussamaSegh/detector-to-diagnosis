# Exercise 33.2: notes

The starter fails 8 of the 11 tests. Its verdicts are right only on the happy path: evidence that
is there, readable, of the candidate and finite.

Design choices:

- The commit is checked before the value. Evidence of another commit says nothing about the
  candidate, whatever its value; reporting it as FAIL would send a reader to look for a
  regression that may not exist, and reporting it as PASS would accept what was never measured.
- A missing `commit` or `dirty` field is MISSING, not STALE: there is no way to tell what the
  evidence is of.
- Only the exceptions that mean "the evidence cannot be read" are caught. A `KeyError` on
  `criterion["limit"]` is a bug in the specification and should stop the run, not become a
  verdict.
- The comparison is written in the positive form, `value >= limit`. With NaN every comparison is
  false, so the positive form fails, and the explicit `isfinite` check turns it into MISSING. The
  starter's negated form, `not value < limit`, is true for NaN: a measurement that produced
  nothing passed.

By hand:

1. `return "FAIL" not in verdicts`. A release asks whether every criterion was shown to be met,
   not whether any was shown to be broken: MISSING and STALE are absence of evidence, and an
   empty list of verdicts is a specification that checks nothing.
2. A pipeline benchmark of last month's commit, at 37 M singles/s, against a limit of 20 M: if the
   target is checked first, the reader sees PASS for a candidate that was never measured, or
   (with an old slow value) a FAIL that sends them hunting for a regression in the wrong commit.
3. `nan >= 20.0` is False and `not (nan < 20.0)` is True. Compare in the form that must be true
   for a pass, and refuse non-finite values before comparing.
