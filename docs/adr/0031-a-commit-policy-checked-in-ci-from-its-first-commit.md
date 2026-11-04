# 0031. A commit policy checked in CI from its first commit, with git's own trailer rule and a trace at the level of a requirement

Date: 2026-11-04
Status: Accepted

## Context

Chapter 36 is about Git and the workflow of a regulated team. MiniDAQ's history is part of its
design and development file: each change request lists its commits, each release record names
the commit it was made from, and each commit message carries the line `Review: change control
checklist, items 1 to 6.` as the record that the checklist was applied. Nothing checked any of
it. The chapter's measurement of the history (`measurements/ch36/`) found that the review line
was never a trailer git parses, that three merges made on the hosting service carry a personal
address in a public history, and that a rule "a commit that changes the SRS names a change
request" would fire on eleven commits after change control began, none of which changed a
requirement.

## Options

1. **Where the rules run.** In a commit-msg hook only; in CI only; or both, the hook for the
   rules that need no history and CI for all of them.
2. **Which commits.** The whole history, with the old commits as accepted exceptions; or the
   commits after a named first commit, with the history before it measured and left as it is.
3. **Trailers.** Any line of the form `Key: value`; or git's own rule (the last paragraph, all
   trailers, or a quarter with a line git generates), checked against `git interpret-trailers`.
4. **The unit of control for the trace.** A file (any change to the SRS, the risk file, the
   software items, the SOUP list or the threat model names a change request); or what the
   procedure of Chapter 16 puts under change control: a requirement's text, item or methods, a
   hazard, a software item.
5. **History that breaks the policy.** Rewrite it; or leave it, record it, and start the policy
   after it.

## Decision

- **Both, the hook and CI** (option 1, the third). The hook gives the answer at the moment it is
  cheapest to fix, and `--no-verify` skips it, so CI is the gate.
- **From a named first commit** (option 2, the second). A policy that reports 977 problems in
  the old history on every run is one that people learn to ignore; the measurement keeps the
  numbers, and the policy's `since` says where it begins.
- **Git's rule for trailers** (option 3, the second). The record must be readable by the tools
  every reader of the history uses, not only by this check.
- **The requirement, the hazard and the item** (option 4, the second). A file-level rule fired on
  eleven commits that updated a requirement's verification evidence or the wording of a plan,
  which the procedure does not route through a request; the requirement-level rule fires on none
  after change control began, and on three before it.
- **Leave the history** (option 5, the second). Every commit name in a change request, a release
  record and a tag would change. The repository's owner chose to leave the three merges with a
  personal address as they are; merges are made locally with the no-reply identity since.

## Consequences

### Positive

- Every commit from now on carries a review trailer that `git log --format=%(trailers)` reads, a
  no-reply identity, and a trace to a request or a report when it changes what the procedure
  controls; a reviewer and an auditor can check that from the history alone.
- The check runs on the whole history in about a second, so it costs nothing to run on every
  push.

### Negative

- The policy checks what a commit says, not who made it: an author's identity is whatever its
  maker typed, and nothing here verifies a signature. Protected branches and signed commits are
  the hosting service's and the team's (threat model, section 7).
- A commit can name a change request without implementing it; the rule checks that the trace
  exists, and the review checks that it is true.
- The old history stays inconsistent with the policy: 254 commits without a parsed review
  trailer and three with a personal address.
- The SOUP list and the threat model are left out of the rule reference: they change at every
  periodic review, which the procedure records without a request.
