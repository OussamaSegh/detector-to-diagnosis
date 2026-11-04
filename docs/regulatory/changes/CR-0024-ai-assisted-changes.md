# CR-0024: The record of AI-assisted changes, and a test with each one

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-11-04, by the software lead |
| Source | improvement: AI-assisted coding for medical-device software (Chapter 37) |
| Decision | approved, 2026-11-04, software lead |
| Commits | df01679 |

## Description

1. **The report** `tools/ai_provenance.py` (TL-47): for a range of commits, those that name an AI
   assistant in their trailers, the software items and classes they changed, the review trailer,
   and the assisted changes of product code that came without a test; as text and as JSON for the
   release record.
2. **The commit policy, version 2**: the patterns that name an assistant (`assistants`) and the
   rule `assisted`: an assisted change of an item's code changes a test or names in a `Tests:`
   trailer the tests that cover it.
3. **The assistant as a tool** (TL-48, class T3) in the tool list, and the rules for its use in the
   development plan, version 13, section 4.
4. **The test** `tools.ai_provenance`.

## Reason

Every commit of MiniDAQ was made with an AI assistant, and nothing recorded what that meant for
the review: which items an assistant changed, and whether each change came with evidence. The
measurement of Chapter 37 (`measurements/ch37/`) found nine assisted changes of product code with
no test changed and none named; all nine were read and are acceptable, and the rule makes the
author say so in the commit from now on.

## Impact analysis

### Requirements

Added (SRS version 26): SRS-AI-001 (which commits are assisted), SRS-AI-002 (items, classes and
tests), SRS-AI-003 (the report), SRS-AI-004 (the rule `assisted`). None changed or withdrawn.
These four are the differences from the requirements baseline that this request names.

### Software items and safety class

None. The report and the rule are tools of the development process (TL-47, class T2); no product
item, hazard or class changes (`tools/check_items.py` passes). The assistant (TL-48) is a tool of
class T3, since what it writes becomes part of the product; that changes how its output is
verified, not the class of any item.

### Risk

None. No hazard, risk control or estimate changes. The rule asks for evidence with each assisted
change; it is not a risk control of a hazard, and the risk file's controls stay verified by their
own tests.

### SOUP

None. The assistant is a development tool, not part of the product; nothing of it ships.

### Interfaces and data formats

None of the product. Commit messages may carry a `Tests:` trailer.

### Documents

The SRS, version 26; the development plan, version 13 (also recording Chapter 36's commit policy
in section 5); the tool list (TL-47, TL-48) and `tools.md`; the threat model, version 12 (the gap
"An AI coding assistant works in the repository with the developer's rights"); ADR 0032; the
trace matrix; the commit policy; the CHANGELOG.

### Regulatory

None for the intended use. Regulators' guidance on AI used in developing device software is
evolving; the development plan states how the assistant is used and how its output is verified,
which is what an auditor will ask (assumption: confirm with team the company's policy on AI
tools and the expectations of its notified body).

## Verification

`tools/test_ai_provenance.py` (the test `tools.ai_provenance`): the trailers that count
(Assisted.test_an_assistant_is_named_in_a_trailer_git_parses), items and tests
(Assisted.test_product_code_belongs_to_the_item_with_the_longest_prefix), the report
(Report.test_counts_and_lists_the_assisted_product_changes_without_a_test) and the rule
(Report.test_the_policy_rule_wants_a_test_or_a_tests_trailer); `tools.commits`, `docs.trace`,
`docs.tools`, `docs.baseline`; the whole ctest. The measurement of the history is kept in
`measurements/ch37/`.

## Decision

Approved on 2026-11-04 by the software lead: a record of the assistant's part in each change and
a test with each change it makes to the product, starting with the next commit.
