# Exercise 21.5 (E): Bisect a regression through commits that do not build

**Goal.** Find the commit that broke a test with `git bisect run`, in a history where some
commits cannot be tested at all. A check that calls such a commit bad blames the wrong commit;
the exit status 125 tells bisect to skip it, and when skipped commits sit next to the defect,
bisect can only name candidates, which your tool must report instead of guessing.

**Time.** 30 minutes.

**Starter.** `starter/bisect_tool.py`: a check for `git bisect run` and a function that runs the
bisection and parses its result. The tests build throwaway repositories whose `app.py` answers
42 until a known commit.

**Tasks.**
1. `check(workdir)`: exit status 125 for a commit whose `app.py` does not import, 0 if
   `app.answer()` is 42, 1 otherwise.
2. `candidates(log)`: return the candidates when bisect cannot decide, from the lines
   `# possible first bad commit: [SHA-1]` of `git bisect log` (newer git writes `'bad'` in
   quotes), not an empty list.

**Acceptance** (`ch21/e5_bisect/<variant>/unittest`, needs git): a clean history; commits that
do not build where bisect tests first, which must be skipped and not blamed; commits that do not
build right before the defect, which must give the three candidates; the log of an older and a
newer git both parse; the repository is left as it was.

Then answer in `NOTES.md`: in MiniDAQ, what would make a commit untestable, and what in the check
would you change so that a skipped build never hides a real failure?
