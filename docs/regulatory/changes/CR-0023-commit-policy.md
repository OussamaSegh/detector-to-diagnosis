# CR-0023: A commit policy that the history is checked against

| Field | Value |
|---|---|
| Status | approved |
| Requested | 2026-11-04, by the software lead |
| Source | improvement: Git and the workflow of a regulated team (Chapter 36) |
| Decision | approved, 2026-11-04, software lead |
| Commits | none yet |

## Description

1. **The policy** `tools/commit_policy.json`, version 1: six rules (identity, subject, layout,
   review, reference, merge), the commit it starts after, the paths under change control and
   the accepted exceptions, each with its commit, its rule and a reason.
2. **The check** `tools/check_commits.py` (TL-46): a range of commits against the policy, with
   git's own rule for trailers and the rule reference at the level of a requirement, a hazard
   and a software item, not of a file.
3. **The commit-msg hook** `tools/hooks/commit-msg`: the four rules that need no history, at the
   moment of the commit, installed with the pre-commit hook of Chapter 32.
4. **CI**: the job document-control runs the check from the policy's first commit to the head
   of the branch, and the test `tools.commits` runs it on the repository when the clone has the
   whole history.
5. **The commit message's form**: the review line moves into the trailer block, with the
   co-author lines, so that git parses it; subjects and bodies at most 72 characters.

## Reason

Chapter 36's measurement of MiniDAQ's own history (`measurements/ch36/`) found that the line
`Review: change control checklist, items 1 to 6.`, written in 191 commits as the record that the
checklist was applied, is in none of them a trailer that git parses: it stands in a paragraph of
its own above the co-author lines, and `git log --format=%(trailers:key=Review)` finds nothing.
Three merges made on the hosting service carry a personal address, which the pre-commit hook
cannot see because it checks the staged changes, not the identity. Nothing checked the commits
themselves; a rule nobody checks drifts.

## Impact analysis

### Requirements

Added (SRS version 25): SRS-GIT-001 (trailers), SRS-GIT-002 (identity), SRS-GIT-003 (subject,
layout and merges), SRS-GIT-004 (the review trailer), SRS-GIT-005 (the trace to a request),
SRS-GIT-006 (the range, the exceptions and the exit status), SRS-GIT-007 (the commit-msg hook).
None changed or withdrawn. These seven are the differences from the requirements baseline that
this request names.

### Software items and safety class

None. The check and the hook are tools of the development process (TL-46, class T2: a defect
lets a commit without its record through, which a reviewer and an audit of the history can
still find); no product item, hazard or class changes (`tools/check_items.py` passes).

### Risk

None. No hazard, risk control or estimate changes. The policy supports the change control that
the risk file's controls rely on (every change reviewed); it is not itself a risk control.

### SOUP

None. The check uses git, which every developer and CI already have, and Python's standard
library.

### Interfaces and data formats

None of the product. The commit message's form changes for new commits (the review line in the
trailer block); old commits stay as they are, and the policy starts after them.

### Documents

The SRS, version 25; the tool list (TL-46) and `tools.md`; the threat model, version 11 (the
gap "The build runs the repository's code" names what the policy checks and what it does not);
ADR 0031; the trace matrix; CI's job document-control; `HANDOFF.md` (the commit message's form);
the CHANGELOG.

### Regulatory

None. The intended use does not change. The check makes the record of change control
(IEC 62304 clause 8 and ISO 13485 clause 7.3.9) checkable in the history itself; it does not
replace the change requests, the review or the design and development file.

## Verification

`tools/test_check_commits.py` (the test `tools.commits`): the trailers against
`git interpret-trailers --parse` (Trailers.test_agrees_with_git_at_the_edges_of_its_rule,
Trailers.test_a_review_line_above_a_blank_line_is_not_a_trailer), the identity
(Rules.test_identity_wants_no_reply_addresses, Range.test_a_merge_made_with_a_personal_address_fails),
subject, layout and merges (Rules.test_subject_and_layout, Rules.test_merges), the review trailer
(Rules.test_review_must_be_a_trailer_git_parses), the trace
(Rules.test_a_controlled_change_names_a_request_or_a_request_names_it,
Range.test_a_requirement_changed_without_a_request_fails_its_verification_does_not), the range
and the exceptions (Range.test_a_good_history_passes_and_starts_after_since,
Range.test_an_accepted_exception_names_its_commit_and_its_rule,
Range.test_a_range_git_cannot_resolve_is_a_usage_error,
OnThisRepository.test_the_policy_holds_from_since), the hook
(Hook.test_the_commit_msg_hook_checks_the_message_and_the_identity); `docs.trace`, `docs.tools`,
`docs.baseline`; the whole ctest. The measurement of the history is kept in `measurements/ch36/`.

## Decision

Approved on 2026-11-04 by the software lead: a tool of the development process that makes the
record every commit already claims to carry checkable, starting with the next commit.
