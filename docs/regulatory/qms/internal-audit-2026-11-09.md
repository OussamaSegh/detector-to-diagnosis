# Internal audit 2026-11-09: plan and practice of MiniDAQ 0.4.0 to 1.0.0

Version 1 (MiniDAQ 1.0.1-dev). Status: final.

| Field | Value |
|---|---|
| Scope | Design and development of MiniDAQ from tag `ch15` to release 1.0.0 (Parts IV to IX): changes and their review, document control, problem resolution, CAPA, SOUP review, release records |
| Criteria | The [SDP](../sdp.md) version 14, the [CAPA procedure](../capa/README.md), the [change control procedure](../changes/README.md), and the clauses of ISO 13485:2016 that the [design file](design-file.md) maps |
| Method | Every commit since CAPA-0002 against the review rule; every controlled document at every release tag against its version at the tag before; every CAPA against its due date and the release records; the tools of the `docs.*` tests run on the audited commit (785456b) |
| Auditor | The book's author, as in the [audit of 2026-10-25](internal-audit-2026-10-25.md): the same limit on independence applies |

It is the first internal audit since 2026-10-25. CAPA-0002's preventive action asked for one
in every Part from Part IV on; none was held (finding A-1).

## Findings

| ID | Requirement | What was found | Classification | Action |
|---|---|---|---|---|
| A-1 | CAPA procedure, step 5: a CAPA is closed only when its criterion is met, checked when it is due | CAPA-0002's effectiveness check, due at release 0.4.0, was never made, and the internal audit per Part that its preventive action promised was not held for Parts IV to IX. The release records of 0.9.0 and 1.0.0 say "No CAPA is open" while CAPA-0002 had the status implemented. `tools/check_capa.py` checked the form of a CAPA, not its due date. | Nonconformity | Problem report MDQ-PR-065; the effectiveness check made at this audit; [CAPA-0002](../capa/CAPA-0002-process-not-as-planned.md) further action; corrections in the records of 0.9.0 and 1.0.0 |
| A-2 | ISO 13485 4.2.4: documents are reviewed and approved before issue | Fifteen of the nineteen controlled documents, the SDP and the SRS among them, carry "Status: draft for review" in the release 1.0.0. The release record approves the release, but no record approves a document at a version, and the status line says it was not. | Nonconformity | Problem report MDQ-PR-066 (open, decision in the report) |
| O-1 | SDP 5: every change reviewed, the review recorded in the commit | 209 of the 210 commits since CAPA-0002 (c957527) carry the line "Review: ..."; the one without, 66d72e8 (the Part VI review, 2026-11-03), is itself a review and predates the commit policy's check (from 34cf130). Since then `tools/check_commits.py` refuses a commit without it. | Observation | None |
| O-2 | ISO 13485 4.2.4: changes to documents identified | `tools/design_file.py --since` at each release tag against the one before, 0.3.0 to 1.0.0 and to the audited commit: no controlled document changed without a new version. Between CAPA-0002 and 0.3.0 two gaps (the audit report of 2026-10-25 changed without a new version, and release record 0.3.0 was in no clause of the design file), both corrected at 0.4.0, the first release at which the check ran in CI. | Observation | None |
| O-3 | SDP 7 and 10: problem reports evaluated; SOUP reviewed at each minor release | `docs.anomalies` (64 reports, 4 open, each with a decision), `docs.soup` (review dated for 1.0), `docs.changes` (25 change requests): all pass. | Observation | None |

## Conclusion

The checks that run by themselves held: document versions since 0.4.0 and the review line in
the commits since the commit policy. What depended on a person remembering a date did not: the
one CAPA whose check had no tool behind it was forgotten for six releases, and two release
records then stated something false about it. A-1 is CAPA-0002's own root cause again (a plan
that nothing compares with the practice); its further action makes the comparison mechanical.

## Document history

| Version | Change |
|---|---|
| 1 | First version (after release 1.0.0, MDQ-PR-065). |
