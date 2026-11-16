# Exercise 40.3: notes

The starter fails three of the six tests: following first parents only, it never reaches a
change that came in on a merged branch's side, so it reports 1.3.0 as clean; looking for the fix
by its id, it calls every maintenance release with the cherry-picked fix affected; and its text
sort puts 1.10.0 before 1.3.0.

Design choices:

- All parents, iteratively, with a set of seen commits: a merge brings a whole branch, and a
  history has many paths to the same commit.
- A cherry-pick is a new commit with another id; only its message says what it copies, which is
  why the maintenance plan requires `-x`. Follow the chain: a pick of a pick names the pick, not
  the original.
- "Contains the defect" is about the introducing commit; "contains the fix" is about any copy of
  the fix. The two questions need different searches, and conflating them is how a release
  record says "not affected" about a branch that never received the fix.
- What it cannot see: a fix rewritten by hand without a trailer, a defect introduced twice, a
  revert of the fix. The record of the change request (which branches it reached) is the second
  source the maintenance plan asks for.
- MiniDAQ's own reports since 1.0.0 were filled in this way, with `git merge-base --is-ancestor`
  between the commits and the tags.
