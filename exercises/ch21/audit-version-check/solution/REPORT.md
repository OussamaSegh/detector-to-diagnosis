# Audit report: the agent's version rules (Exercise 21.6)

Not mergeable. The "more robust" rule accepts exactly the state the rules exist to prevent,
and the anchored pattern accepts a version followed by a newline. Both are MiniDAQ's own
defects.

## Defect 1: the newest release's version passes on any commit (MDQ-PR-024)

To accept the tag-list commit without matching its subject, the agent accepts the newest
release's version everywhere. A main branch whose VERSION was never moved after the release
then passes on every commit until the next release.

- *Test:* `test_a_release_version_in_any_later_commit_is_refused`.
- *What an investigator does:* reads a crash report of an unreleased build that says 0.3.0,
  checks out the release, and debugs code that did not crash. List-mode files written by
  every build of main name the released version too. This is what happened to MiniDAQ after
  release 0.3.0: Chapters 16 to 20 were built as 0.3.0 (found in this chapter, with the first
  crash report).
- *Correction:* accept a release version only in its release commit and in the commit that
  lists its tag (`Tag book-vX.Y.Z `, MDQ-PR-091). Matching that subject is the rule, not a
  fragility: a release has exactly those two commits.

## Defect 2: a version followed by a newline passes (MDQ-PR-084)

`re.match` with `^...$`: Python's `$` also matches just before a final newline, so
`"0.4.0-dev\n"` and `"0.4.0\n"` pass the pattern. The specification says nothing after the
version.

- *Test:* `test_text_that_is_not_a_version_is_refused`.
- *Effect:* the newline is carried into every program's version string: the hello, the crash
  report and every list-mode file's software field get a version with a line break in it, and
  a tool that compares versions sees two different ones. MDQ-PR-084 found the same pattern in
  four validations of MiniDAQ, a release version among them.
- *Correction:* `re.fullmatch` (coding standard rule 3.6; the agent gate's `validation` check
  refuses this pattern in product code).

## Verdict

Request changes. An agent that replaces a rule of the specification with "something more
robust" has changed the specification: ask which case the new rule accepts that the old one
refused, before asking whether it is robust.
