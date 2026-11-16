# Exercise 40.3 (H): Which releases contain a defect

**Goal.** Given a history of commits, the release tags, the commit that introduced a defect and
the commit that fixed it on main, list the released versions that contain the defect: the
"affects" of a problem report (maintenance plan, section 2).

**Time.** 3 hours.

**What to write** (`affected.py`): `affected(commits, tags, introduced, fix)`. `commits` maps a
commit id to `{"parents": [ids], "message": text}`, a merge having two parents; `tags` maps a
version to the commit it tags. A version is affected when its commit's history (every ancestor,
through every parent, the commit itself included) contains `introduced` and contains neither
`fix` nor a copy of it. A copy is a commit made by `git cherry-pick -x`, whose message ends
with `(cherry picked from commit <id>)` naming the commit it copied; a copy of a copy counts.
Return the versions sorted as numbers. The walk must not recurse: a history of 20,000 commits
is the test.

**Starter.** `starter/affected.py` follows first parents only, looks for the fix by its own id,
and sorts the versions as text.

**Acceptance** (`tests/test_affected.py`): a defect that came in on a merged branch, a fix
cherry-picked to a maintenance branch and picked again from there, a release branch made before
the defect, a defect fixed before any release, and a long history.

**Then, by hand.**
1. Run `git tag --contains <commit>` on a repository you know. Why does it answer "which releases
   contain the defect" but not "which releases contain the fix"?
2. A fix that did not cherry-pick cleanly was written again for the maintenance branch, without
   `-x`. How would you record that the branch has the fix, so that this function still sees it?
3. Find the commit that introduced a defect when you know only the commit that fixed it. What does
   `git bisect` need, and what can `git blame` on the fixed lines tell you, and not?
