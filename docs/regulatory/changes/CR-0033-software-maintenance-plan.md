# CR-0033: Software maintenance plan, affected releases and SOUP end of support

| Field | Value |
|---|---|
| Status | approved |
| Requested | 2026-11-16, by the software lead |
| Source | roadmap 2.0.0, theme C (Chapter 40); IEC 62304 clause 6.1, for which the SDP had four lines; OpenSSL 3.0's end of support by its project on 2026-09-07, which no record noticed |
| Decision | approved, 2026-11-16, under the software lead's standing delegation of 2026-11-15 |
| Commits | listed when the change is implemented |

## Description

MiniDAQ gets a software maintenance plan, and the records it relies on are checked (ADR 0039).

1. **The plan** (`docs/regulatory/maintenance-plan.md`, a controlled document, version 1):
   feedback, evaluation, supported releases (24 months, an assumption), kinds of release and
   maintenance branches, SOUP over the years, trends, retirement. SDP section 10 points to it.
2. **Affected releases** (`tools/anomalies.py`): `affects` in each problem report from
   MDQ-PR-065 on and in each open one, checked against the releases in CHANGELOG.md; filled in
   for MDQ-PR-006, MDQ-PR-064 and MDQ-PR-065 to MDQ-PR-073 from the git history (the first tag
   that contains the introducing change, and the first that contains the fix); the known
   anomalies gain a column "In releases" (SRS-MNT-001).
3. **SOUP end of support** (`tools/check_soup.py`, SOUP list version 29): `Support ends` for each
   shipped item, and an `End-of-support plan` when it ends within 24 months of the item's last
   review: OpenSSL has one (SRS-MNT-002).
4. **Trends** (`tools/pr_trends.py`, tool TL-50): the problem reports per release window
   (SRS-MNT-003); its first output in `measurements/ch40/trends.txt`.

## Reason

After thirteen releases, three questions had no recorded answer: which installed releases a
problem affects, how long a release is supported and what a patch may contain, and what happens
when a SOUP supplier stops supporting its item. The last one had already happened: OpenSSL 3.0
left the OpenSSL project's support on 2026-09-07, and the SOUP list's reviews went on reading the
project's advisories as if it were supported.

## Impact analysis

### Requirements

Added: SRS-MNT-001 to SRS-MNT-003 (SRS version 36), each verified by test (`tools.maintenance`).
No requirement of the shipped programs changes.

### Software items and safety class

None of MiniDAQ's software items changes. The change is in the tools that check the project's
records (`tools/anomalies.py`, `tools/check_soup.py`, new `tools/pr_trends.py`) and in the
records themselves.

### Risk

No hazard changes. The end-of-support plan for OpenSSL is a SOUP decision: the fixes of the
platform's OpenSSL now come from the distribution's security maintenance (Ubuntu 24.04 LTS,
standard support until 2029-05), which the known-anomaly review reads first; the threat model's
reliance on the platform's security updates (threat-model.md, section 6, item 7) is unchanged.

### SOUP

No item added or changed. The SOUP list records each shipped item's end of support (version 29).

### Interfaces and data formats

None. `problem-reports.json` gains an optional field, required from MDQ-PR-065 on; the known
anomalies gain a column.

### Documents

The maintenance plan (new, controlled); the SDP (section 10, version 18); the SRS (version 36);
the SOUP list (version 29); the tool list (TL-50); the design file index (clause 8.2.1 and the
controlled documents); ADR 0039; Chapter 40; the CHANGELOG.

### Regulatory

The intended use does not change. The plan answers IEC 62304 clause 6.1 for this project.

## Verification

Tests: `Affects`, `SupportEnds` and `Trends` in `tools/test_maintenance.py` (`tools.maintenance`);
`docs.anomalies`, `docs.soup`, `docs.srs`, `docs.trace`, `docs.baseline`, `docs.design_file`,
`docs.changes`, `docs.tools`; the whole ctest.

## Decision

Approved on 2026-11-16 by the coordinator under the standing delegation that the software lead
gave on 2026-11-15 for the work towards 2.0.0, after reading the impact analysis above.
