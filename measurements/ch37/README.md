# Chapter 37 measurements: how MiniDAQ was built with an AI assistant

`provenance.txt` is the output of
`python3 measurements/ch37/provenance.py measurements/ch37/provenance.txt` in a whole clone (a few
seconds). It prints counts and abbreviated commit names only. The commit it was measured at is on
its first line.

What it shows:

1. Every commit of MiniDAQ that is not a merge names an AI assistant in a `Co-Authored-By:`
   trailer: the book and its code were written by an author working with an assistant, as the
   copyright page says. 52 assisted commits changed product code; 9 of them changed no test in
   the same commit. Each of the nine was read: six are comment, assertion and warning fixes
   (a `static_assert`, a `NOLINT` with its reason, clang-tidy and `-Wdouble-promotion` findings,
   comments made product-neutral), one is an optimization of the simulator's replay loop, one is a
   change of behavior (`minidaq_server` sends READY before the watchdog starts) that the system
   test `system.platform` had caught, and one is a robustness fix (no exception escapes the
   simulator's `main` or the sink's destructor) whose message names no test. The commit policy's
   rule `assisted` would have asked each of them to name its tests in a `Tests:` trailer.
2. The rule over the whole history: the same nine; none since the policy began.
3. The 60 problem reports by what found them: the release checks and their reviews found the
   most (20), then CI runs (14), the author's own tests and runs (12), design and measurement (6),
   fuzzing (5), the independent reviews of the Parts (2), an internal audit (1). The classes are
   keyword rules on the field `found` of each report (`SOURCES` in the script), not a judgment of
   each report.
4. Five independent reviews, one per Part from Part IV on, each by a separate session that had not
   written the Part: each one commit, together 37 files changed. For Parts IV to VI most of them
   were in the book (numbers, claims, layout); for Parts VII and VIII most were in the code and the
   records, and the review of Part VIII opened the two problem reports.

`mutants.txt` is the output of `python3 measurements/ch37/mutants.py measurements/ch37/mutants.txt`
(a few seconds, a C++17 compiler). It compiles the two tests of Exercise 37.3's starter and the
eight of its solution against each of the eight versions of `assisted::coincident` and records
which test fails on which version. The starter's two tests catch none of the seven mutants; the
solution's catch all seven. Three mutants are caught by one test only: the wrap forgotten (2) by
the test across the wrap, the inputs masked (4) by the invalid timestamps, the window unlimited
(7) by the window of half the period. The two tests the solution keeps from the starter catch
nothing.
