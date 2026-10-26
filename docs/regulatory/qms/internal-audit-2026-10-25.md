# Internal audit 2026-10-25: design and development of MiniDAQ 0.3.0-dev

Version 2 (MiniDAQ 0.4.0-dev, release 0.4.0). Status: final.

| Field | Value |
|---|---|
| Scope | Design and development of MiniDAQ from Chapter 1 to tag `ch15`: planning, inputs, outputs, verification, changes, document and record control, problem resolution |
| Criteria | The [SDP](../sdp.md) version 2, the [design and development file](design-file.md), and the clauses of ISO 13485:2016 that it maps |
| Method | Sampling: the coincidence sorter from requirement to test, every controlled document against its git history, every commit that fixed a test, the control API against ADR 0003, the SOUP review against the library's source |
| Auditor | The book's author. ISO 13485 asks that auditors do not audit their own work; in this teaching project nobody else can, so the findings below are weaker evidence than an independent audit's (assumption: confirm with team who audits the NeuroLF's software process) |

## Findings

| ID | Requirement | What was found | Classification | Action |
|---|---|---|---|---|
| A-1 | SDP 5: every change is a pull request, reviewed by someone who did not write it | The repository's main branch receives commits directly; no change has a record of a review by another person. The Part reviews at the end of Parts I and II are recorded in the CHANGELOG. | Nonconformity | [CAPA-0002](../capa/CAPA-0002-process-not-as-planned.md) |
| A-2 | ISO 13485 4.2.4: documents are reviewed, versioned, and their changes identified | Seven of the ten controlled documents, all written before Chapter 14, had no change history; the SDP, the SRS and the risk management plan had one. The performance budget changed in Chapters 5, 7, 11 and 12 without any version, and the MDQ-L1 specification had none. | Nonconformity | Corrected in Chapter 16: versions and history tables, checked by `docs.design_file` and, against the last release, by `tools/design_file.py --since` in CI. Recorded in [CAPA-0002](../capa/CAPA-0002-process-not-as-planned.md) |
| A-3 | ADR 0003: new response fields only in a new minor version | The status gained four top-level fields while the API stayed 1.0. | Nonconformity of the product | Problem report MDQ-PR-012, [CR-0003](../changes/CR-0003-api-1.1-status-fields.md) |
| A-4 | SDP 7: a problem found after a change is merged is recorded as a problem report | Two test failures after merge (commits `7f01a94` and `3ea28f5`) were fixed without problem reports; the same cause was found in more tests. | Nonconformity | Problem reports MDQ-PR-010 and MDQ-PR-011, [CAPA-0001](../capa/CAPA-0001-timing-dependent-tests.md) |
| O-1 | SOUP review (Chapter 14) | The evaluation of MDQ-PR-005 rested on a cause marked "verify" that reading the library's lexer showed to be wrong. The marking worked as intended: the claim was checked before a decision depended on it. | Observation | MDQ-PR-005 corrected; closed by [CR-0002](../changes/CR-0002-nlohmann-json-3.12.0.md) |
| O-2 | ISO 13485 7.3.7: design validation | No validation evidence, as expected for a component: validation is of the scanner (plan in the design file). | Observation | None |

The sample of the sorter (Exercise 16.3) traced every requirement to a test that exists and
passes, found its risk analysis, its design decision and its known anomaly where the design
file says, and confirmed finding A-1 for its last change.

## Conclusion

The design outputs are verified and traceable; the process that produced them did not follow
its own plan in four places, all of them in how changes were recorded rather than in what was
built. The corrections are in place for MiniDAQ 0.3.0; the effectiveness of the two CAPAs is
checked at the release of 0.4.0.

## Document history

| Version | Change |
|---|---|
| 1 | First version (Chapter 16). |
| 2 | Editorial: the repository's history was rewritten to remove personal data, so the cited commit hashes are those of the rewritten commits; the content is unchanged. |
