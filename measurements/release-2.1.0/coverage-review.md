# Release 2.1.0 structural coverage review

The review that the development plan asks of a release (SDP section 6, structural coverage): every
branch and condition that the tests never took both ways on a line of a class B file changed since
release 2.0.1 (tag `book-v2.0.1`). The lines come from the `coverage` build of the release checks
(commit dae4498), read by `tools/coverage.py --uncovered`, restricted to the lines that
`git diff -U0 book-v2.0.1 dae4498` adds or changes in class B source. The totals per software
item are in `coverage.txt`.

## Lines changed since 2.0.1

None. `git diff --name-only book-v2.0.1 dae4498 -- minidaq` lists no file: no source of a
shipped software item changed in 2.1.0. The one C++ source that changed,
`recon/python/recon_cpp.cpp` (CR-0034), is the reconstruction tool's module (TL-31), not a
shipped item, and its tests are `tools/test_recon_cpp.py` and `recon.wheel`.

## Finding

None: there is no changed class B line to review.

## Items whose branch coverage differs from 2.0.1

Lines are 10,232 of 11,252 against 10,231, and branches 4,503 of 5,548 in both releases. Four
items differ by one branch each, with no change to their source:

- `rt` 164 to 163 of 214, `protocol` 224 to 223 of 264, `hw` 280 to 279 of 316 (lower);
- `output` 220 to 221 of 294 (higher).

A branch that a run takes or not with the same source and the same tests depends on the schedule
of that run (a timeout, a retry, a thread that arrives first), as with the flight recorder's
merge at 2.0.1. The run of 2.0.1 kept the totals per item only, so the four branches are not
named line by line; none of the items' code changed, so no requirement's verification changed.
