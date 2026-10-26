# Exercise 21.5: notes on the solution

**Skip, never bad.** A commit that cannot be tested says nothing about the defect. Calling it bad
moves the search before it: with commits 18 to 21 broken and the defect in 25, the starter's
check blames commit 18. Exit status 125 tells `git bisect run` to skip the commit and test a
neighbor. When the skipped commits are next to the defect (23 and 24 broken, 25 bad), bisect
cannot decide among 23, 24 and 25, and `git bisect log` lists all three as possible first bad
commits; the honest result is the three candidates, and the next step is to read those three
diffs.

**Read the log, not the messages.** The second version parsed what `git bisect run` prints. It
passed with git 2.43 and failed on GitHub's runners with git 2.55, where it found neither message in
the output. The log's comment lines are the record bisect keeps for tools and people alike.

**A stale cache can lie.** The first version of this solution failed three tests for a reason
that had nothing to do with bisect: `app.py` had the same size in every commit and git checked
out each version within the same second, so Python's `.pyc` cache, which compares the source's
modification time and size, ran the bytecode of an earlier commit. Every commit looked good.
The check now runs Python with `-B`. A check that reads build outputs must start from a clean
state, or bisect searches the cache instead of the history.

**In MiniDAQ.** A commit is untestable when it does not configure or compile (a half-finished
refactoring, a dependency that is no longer downloadable), or when a test other than the one
under investigation fails first. A good check builds only the target it needs, runs only the
test that shows the defect, returns 125 for a failed build and for a missing dependency, and 1
only for the failure it looks for, matched by its message, so that an unrelated crash is a skip
and not a verdict. Every skipped commit is listed in the problem report, because a skip hides a
range of history from the search.
