# Internal audit 2026-11-10: plan and practice before release 1.1.0

Version 1 (MiniDAQ 1.1.0-dev). Status: final.

| Field | Value |
|---|---|
| Scope | Design and development of MiniDAQ since the [audit of 2026-11-09](internal-audit-2026-11-09.md) (its audited commit 785456b) up to the candidate of release 1.1.0: changes and their review, document control and approval, problem resolution, CAPA, SOUP review, the release checks |
| Criteria | The [SDP](../sdp.md) version 16 (section 8, item 9: an internal audit before each minor release), the [CAPA procedure](../capa/README.md), the [change control procedure](../changes/README.md), and the clauses of ISO 13485:2016 that the [design file](design-file.md) maps |
| Method | Every commit since 785456b against the commit policy (`tools/check_commits.py`); every controlled document against its version at release 1.0.0 (`tools/design_file.py --since book-v1.0.0`) and against the status a release requires; every CAPA against its due release; the tools of the `docs.*` tests run on the audited commit |
| Auditor | The book's author, as in the audits of 2026-10-25 and 2026-11-09: the same limit on independence applies |

It is held before the release checks of 1.1.0 that the release record cites, as the SDP asks
since the audit of 2026-11-09 (MDQ-PR-065). A first run of the release checks, on 039e718 before
this audit, passed every part; it is not the evidence of the release, because it came before the
audit (finding O-4).

## Findings

| ID | Requirement | What was found | Classification | Action |
|---|---|---|---|---|
| O-1 | SDP 5: every change reviewed, the review recorded in the commit | 55 commits since 785456b, one of them a merge (219e408, the illustrated interior with main's index): `tools/check_commits.py . 785456b..HEAD` reports 0 problems under commit policy 2, the review line among its rules. | Observation | None |
| O-2 | ISO 13485 4.2.4: changes to documents identified | `tools/design_file.py . --check --since book-v1.0.0`: no controlled document changed without a new version. | Observation | None |
| O-3 | ISO 13485 4.2.4: documents approved before issue (MDQ-PR-066) | On 2026-11-10 the software lead approved the fifteen documents that said "draft for review", each at its content of 1.0.0, recorded as a new version of each; the SOUP list's routine review for 1.1 was added the same day and is in its approved version. `tools/design_file.py` now refuses a draft in a release. The ICD-FEB records the software lead's approval; the firmware lead's co-signature that the ICD asks for is not recorded (assumption: confirm with team). | Observation | MDQ-PR-066 closed |
| O-4 | SDP 8: the release checks run on the commit to be released, after this audit | The release checks first ran on 039e718, before this audit and before the approvals; every part passed. They are run again on the commit that holds this report, which is the candidate. | Observation | Release checks again |
| O-5 | SDP 6: CI on every change | The workflows `kdp` and `pages` failed on 039e718: the figures of the illustrated interior import Matplotlib and NumPy, which their runners did not install. Fixed in 1a0fa8c (a virtual environment from `analysis/requirements.lock`). No product file was concerned. GitHub Actions had not run at all from 2026-11-09 19:45 to the next morning (a billing lock on the account). | Observation | None |
| O-6 | CAPA procedure, step 5 | CAPA-0002's criterion for 1.1.0 (no controlled document changed without a new version and no commit without its review line since its result of 2026-11-09; the release record cites this audit; `docs.capa` passes on the release commit): the first two hold (O-1, O-2); the other two are checked on the release commit. | Observation | Result recorded in CAPA-0002 at the release |
| O-7 | SDP 7 and 10 | `docs.anomalies` (66 reports, 4 open, each with a decision), `docs.soup` (review dated for 1.1), `docs.changes` (25 change requests), `docs.capa`: all pass. | Observation | None |

## Conclusion

No nonconformity. The two checks that CAPA-0002 put in tools held for every change since the last
audit, and the one that rested on a person, the approval of documents, is now a release step with
a check behind it.

## Document history

| Version | Change |
|---|---|
| 1 | First version, before the release checks of 1.1.0. |
