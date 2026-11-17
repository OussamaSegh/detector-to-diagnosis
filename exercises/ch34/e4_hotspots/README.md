# Exercise 34.4 (M): Hotspots, and what a threshold leaves out

**Goal.** Rank the files a newcomer should read first by commits times code lines, as
`tools/survey.py` does, but without the three distortions the chapter warns about: commits that
touch everything (a reformat, a license header, a mass rename), a file whose history is split
across its old names, and history older than the window you care about.

**Time.** 1 hour.

**Starter.** `starter/hotspots.py`, with `rename(path)`, `commits(text)` and
`hotspots(text, sizes, since, mass)`, which returns `(ranking, mass_commits)`. The input is the
text of `git log --numstat --format='commit %H %as'`. The starter counts every commit, keeps a
renamed path as numstat writes it, ignores the window, and breaks ties arbitrarily.

**Acceptance** (`tests/test_hotspots.py`, run by `ctest --test-dir build/debug -R ch34/e4`):
- Scores are commits times code lines, highest first, every current file listed.
- A commit touching more than `mass` files is left out and listed; the large file it touched
  keeps 0 commits.
- `rename` reads `src/{old => new}/a.cpp`, `src/{ => core}/a.cpp` and `a.cpp => b.cpp`, and a file
  renamed twice counts all four of its commits under its current name.
- Commits before `since` are left out; a binary file's `-` counts still count its commit.
- Equal scores are ordered by path.

**Then, by hand.**
1. Run your function on MiniDAQ: `git log --numstat --format='commit %H %as' -- minidaq`, with
   the non-blank code lines of each `.cpp` and `.hpp` as sizes. How many commits touch more than
   20 files, what are they, and what do they do to the top five?
2. Compare with `churn` in `tools/survey.py`. Which of the three distortions does it handle, and
   what does it do with a commit made before a rename?
3. Is a threshold of 20 files right for every project? What else could tell a reformat from a
   real change?

**Hints.** `git log` lists the newest commit first, so a rename is seen before the commits that
used the old name: keep a map from old names to current ones as you go. Count a commit once per
file even if the file appears twice.
