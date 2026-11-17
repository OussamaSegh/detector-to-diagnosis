# Exercise 36.4: notes on the solution

## 1. What the starter answered

With commits 49 to 51 untestable and the first bad one at 37, the starter took 50 as good on its
first step, moved the good end past the real answer, and named commit 52, fifteen commits too late.
With commit 37 untestable and the first bad one at 38, it named 38. With a build broken from 20 to
25 and the first bad one at 23, it named 26. Each answer was a single commit, stated as plainly as a
correct one, and two of them were wrong without any sign: a reviewer reading "first bad commit: 52"
would have read the wrong change and found nothing. The case of 38 happens to be right, but only by
luck: the defect could as well have come with 37, which nobody could test.

## 2. Against Git

On 60 commits whose test fails from the 24th (`c023`) and exits 125 from the 21st to the 26th,
`git bisect run` (Git 2.43) printed "There are only 'skip'ped commits left to test. The first bad
commit could be any of:" and the seven commits `c020` to `c026`, after 11 test runs. The solution
gives the same seven after 10. Git chooses among untestable neighbors with a pseudo-random bias
away from the skipped commit rather than strictly the nearest one, so the number of runs can differ
by one or two; the candidates cannot, because they are fixed by the last good and first bad commits
the tests established.

## 3. Other reasons for 125

A commit on which the test cannot run for a reason unrelated to the defect: a dependency or a test
fixture that did not exist yet, a test that needs hardware the commit's code cannot drive, a data
format the commit cannot read, a flaky infrastructure step. The rule is that 125 means "no
information", never "probably good". A history whose every first-parent commit passed CI builds
and runs its tests at every commit `git bisect --first-parent` visits, so untestable commits are
rare there; they come back when the test being bisected is newer than the commits, and has to be
applied to them from outside.
