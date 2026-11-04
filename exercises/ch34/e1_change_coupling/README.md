# Exercise 34.1 (E): Files that change together

**Goal.** From a repository's history, find the pairs of files that are changed in the same
commits. A new engineer learns from them what the documents do not say: change the decoder and you
will change the simulator's link model too; change the configuration schema and three tests
follow.

**Time.** 1 hour.

**The input.** The output of `git log --name-only --format=@%H`: a line `@<hash>` per commit,
followed by the files it changed, one per line, and blank lines.

**What to compute.** `coupling(log, min_shared=2, max_files=20)` returns a list of
`(a, b, shared, degree)` with `a < b`, where `shared` is the number of commits that changed both
files and `degree = shared / min(commits of a, commits of b)`, the share of the less often changed
file's commits that also changed the other. Leave out:

- pairs that share fewer than `min_shared` commits;
- commits that change more than `max_files` files: a mass rename or a reformatting makes every pair
  of its files look coupled.

Sort by `shared`, then `degree`, both descending, then by `a` and `b`.

**Starter.** `starter/coupling.py` counts every ordered pair twice, keeps large commits, ignores
`min_shared`, and counts a file's commits including those it left out.

**Acceptance** (`tests/test_coupling.py`):
- Two files changed together in three commits, one of them also alone in a fourth: shared 3,
  degree 1.0, listed once.
- A commit of 21 files adds nothing; one of 20 counts.
- A pair below `min_shared` is left out; the order of the list is the one above.
- An empty log gives an empty list.

**Then, by hand.**
1. Run the solution on MiniDAQ's history (`git log --name-only --format=@%H -- minidaq/`). Which
   pair of files is most coupled? Is the coupling one the architecture explains, or one it hides?
2. Why divide by the smaller count and not the larger? What would a degree of 1.0 with the larger
   count mean?
3. Name two reasons a pair can be coupled in the history without any dependency in the code.

**Hints.** `itertools.combinations(sorted(set(files)), 2)` gives each unordered pair once.
