# Exercise 36.4 (M): A bisection that knows what an untestable commit leaves open

**Goal.** `git bisect run` takes exit code 125 to mean "this commit cannot be tested": it does not
build, or the test cannot run on it. Write the bisection that handles it as Git does: it tests
other commits near the middle, and when only untestable commits are left between the last good and
the first bad one, it says that the first bad commit could be any of them, instead of naming one.

**Time.** 1 hour.

**Starter.** `starter/first_bad.py`, with `bisect(commits, good, bad, test)`, which returns
`(first_bad, candidates, tested)`. `commits` is a first-parent history, oldest first; `test(commit)`
returns `"good"`, `"bad"` or `"skip"`. The starter halves the range and takes a commit that cannot
be tested as good.

**Acceptance** (`tests/test_first_bad.py`, run by `ctest --test-dir build/debug -R ch36/e4`):
- Without untestable commits, the first bad commit of 100 is found with at most 7 tests, wherever
  it is.
- Three untestable commits far from it change nothing.
- An untestable commit just before the first bad one leaves both as candidates, and no single
  answer.
- A build broken for six commits around the first bad one gives all seven candidates, and no
  commit is tested twice.
- Only commits strictly between good and bad are tested; adjacent good and bad need no test.
- Good not before bad, a commit outside the history, and a test that answers anything else raise
  `ValueError`.

**Then, by hand.**
1. What did the starter answer in each of the three cases with untestable commits? Which of its
   answers would a reviewer have believed?
2. Make a repository of 60 commits whose test fails from the 24th and cannot run on the 21st to
   26th, and run `git bisect run` with a script that exits 125 there. Compare Git's candidates and
   its number of tests with yours.
3. A commit that does not build is one reason for 125. Name another, and say why a project that
   requires every first-parent commit to pass CI rarely needs it.

**Hints.** Keep the last good and the first bad index and a set of skipped ones; pick the untested
commit nearest the middle of what is left; stop when every commit strictly between them is
skipped. The candidates are the skipped ones there and the first bad one.
