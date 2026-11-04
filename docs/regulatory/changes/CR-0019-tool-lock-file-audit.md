# CR-0019: Audit of the tools' lock file, Pillow 13.0.0 and Pygments 2.21.0

| Field | Value |
|---|---|
| Status | approved |
| Requested | 2026-11-04, by the software lead |
| Source | problem report MDQ-PR-051, found by the SOUP review for release 0.7.0 |
| Decision | approved, 2026-11-04, software lead |
| Commits | none yet |

## Description

`analysis/requirements.lock` pins Pillow 13.0.0 (was 12.3.0) and Pygments 2.21.0 (was 2.17.2).
A new tool, `tools/lock_audit.py` (TL-39), looks up every pinned version in the Python Package
Index's vulnerability records and fails for one with a published advisory; CI's job `python`
runs it on every push, and its tests run as `tools.lock_audit`.

## Reason

Two pinned packages had published vulnerabilities that no review or check reported (MDQ-PR-051).
The vulnerability scan covers the SBOM of the shipped programs, not the tools that produce the
evidence; without the audit, a tool keeps a defect that its supplier has fixed until someone
happens to look.

## Impact analysis

### Requirements

None added or changed: the change concerns tools.

### Software items and safety class

None of the product's items changes. The analysis package's code is unchanged.

### Risk

No hazard changes. H-14 (a QC report computed wrongly) keeps its controls RC-45 and RC-46; the
upgraded packages are verified by the same tests.

### SOUP

Section 2 of the SOUP list (version 15): Pillow and Pygments upgraded in the lock file, with the
known-anomaly review for release 0.7.0. No item of the shipped software changes.

### Interfaces and data formats

None.

### Documents

The SOUP list, version 15; the tool list (TL-39) and `tools.md`; the threat model, version 7
(section 8); the problem report MDQ-PR-051; the CHANGELOG.

### Regulatory

The intended use of MiniDAQ does not change.

## Verification

The tests tools.lock_audit (among them
LockAudit.test_a_pinned_version_with_an_advisory_is_reported_with_its_fix and
LockAudit.test_a_record_without_the_field_is_an_error_not_a_clean_result), analysis.pytest,
analysis.mypy, analysis.ruff and recon.wheel with the new pins; `pip check`; `tools/lock_audit.py
analysis/requirements.lock` reports 28 packages and none affected.

## Decision

Approved on 2026-11-04 by the software lead: tool versions raised to fix published
vulnerabilities, verified by the tests of the tools that use them.
