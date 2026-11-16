# Internal audit 2026-11-16: plan and practice before release 2.0.0

Version 2 (MiniDAQ 2.0.0-dev). Status: final.

| Field | Value |
|---|---|
| Scope | Design and development of MiniDAQ since release 1.3.0 (tag book-v1.3.0) up to the candidate of release 2.0.0: the six changes of the release (CR-0028 to CR-0033) and their review, document control and approval, problem resolution, CAPA, the SOUP review and its end-of-support dates, the maintenance plan, the readers of the files MiniDAQ writes |
| Criteria | The [SDP](../sdp.md) version 18 (section 8, item 9: an internal audit before each minor or major release), the [maintenance plan](../maintenance-plan.md) version 1 (section 6, trends), the [CAPA procedure](../capa/README.md), the [change control procedure](../changes/README.md), the [coding standard](../../coding-standard.md) rule 3, and the clauses of ISO 13485:2016 that the [design file](design-file.md) maps |
| Method | Every commit since book-v1.3.0 against the commit policy (`tools/check_commits.py`); every controlled document against its version at release 1.3.0 (`tools/design_file.py --since book-v1.3.0`) and against the status a release requires; every change request's status against its commits; every CAPA; `tools/pr_trends.py` for the window of 2.0.0; every call of `json::parse` in `minidaq/src` and `minidaq/apps` against coding standard rule 3; the tools of the `docs.*` tests run on the audited commit |
| Auditor | The book's author, as in the earlier audits: the same limit on independence applies |

It is held before the release checks of 2.0.0 that the release record cites, as SDP section 8,
item 9 asks.

## Findings

| ID | Requirement | What was found | Classification | Action |
|---|---|---|---|---|
| O-1 | SDP 5: every change reviewed, the review recorded in the commit | 29 commits since book-v1.3.0 before this audit's own: `tools/check_commits.py . book-v1.3.0..HEAD` reports 0 problems under commit policy 2. | Observation | None |
| O-2 | ISO 13485 4.2.4: changes to documents identified | `tools/design_file.py . --check --since book-v1.3.0`: 20 clauses, 24 controlled documents (the maintenance plan is new), no controlled document changed without a new version. | Observation | None |
| N-1 | Change control procedure: a change request records its implementation | CR-0028 (C++23), CR-0029 (product build without the simulator) and CR-0030 (control API 3.0, configuration schema 2.0), the three breaking changes of the release, were implemented on 2026-11-15 and 2026-11-16 but still said "approved", with "none yet" or "see the CHANGELOG" as their commits; CR-0031 to CR-0033 had each been moved to "implemented" in a follow-up commit. `docs.changes` checks an implemented request's commits and tests but cannot see that the work of an approved one is done. Nothing in the release depended on the status, but a reader of the change requests could not tell that the breaking changes were made. | Minor nonconformity | Corrected in 198407f: each lists its commit and names its tests. `docs.changes` now also reads the system tests' names, where CR-0029's refusals are tested. No CAPA: the cause is one omitted follow-up step, the procedure already asks for it, and the release record lists every change request with its status |
| O-3 | Change control procedure: a change approved before it is made | CR-0028 to CR-0033 were approved before their commits by the coordinator under the software lead's standing delegation of 2026-11-15. CR-0029 and CR-0030 are breaking; each has its migration path (`docs/migration-2.0.md`, `tools/migrate_config.py`, TL-49) and is named in the CHANGELOG's breaking section. | Observation | The release notes of 2.0.0 name CR-0029 and CR-0030 as breaking |
| O-4 | ISO 13485 4.2.4: documents approved before issue | Eight controlled documents said "draft for review": the SDP version 18, the SRS version 36, the SOUP list version 29, the maintenance plan version 1, the architecture version 26, the coding standard version 8 (version 9 after N-2), the STP version 3 and the ICD of the front-end boards version 5. `tools/design_file.py` refuses a draft in a release. The coordinator approved the eight for release 2.0.0 on 2026-11-16 under the standing delegation, on the condition that the approvals are recorded after the review of the release candidate is merged, against the versions as they stand then. | Observation | Recorded on 2026-11-16 after the review (PR #18) was merged, before the release checks, against the versions as they then stood: SDP version 19, SRS version 37, SOUP list version 30, maintenance plan version 2, architecture version 28 (the review's version 27), coding standard version 10 (version 9, after N-2, approved by the coordinator on being told what changed), STP version 5 (the review's version 4) and ICD-FEB version 6 |
| O-5 | SDP 7.3, the SOUP list: known vulnerabilities assessed; maintenance plan 5: end of support | The review for MiniDAQ 2.0 (SOUP list section 4, 2026-11-16) found no new advisory that affects MiniDAQ. CR-0033 found that the OpenSSL project's support for 3.0, the series of the platform's package, ended on 2026-09-07, two months before any record noticed: no record asked for the date. Every shipped item now records when its support ends, and OpenSSL 3.0 has an end-of-support plan (`docs.soup`). | Observation | None further: the check now exists |
| N-2 | Coding standard rule 3.4: each parser of external input has a fuzz target; rule 3.5: types checked before values are read | MDQ-PR-071 had reached release 1.3.0 by the cause that CAPA-0003 removed in 0.4.0, which the maintenance plan (section 6) asks to evaluate for a CAPA. Reading every call of `json::parse` found five readers of files without a fuzz target (the hardware description, the update manifest, the token file, the signed run record, the update store's state) and two more defects of the same kind, both released since early versions: the update store's `state.json` with a version of another type (MDQ-PR-074) and the delayed window in list-mode metadata (MDQ-PR-075). Reading the Python readers of the same files found a third (MDQ-PR-076). Rule 3 did not name the files MiniDAQ writes and reads again. | Minor nonconformity | CAPA-0005: coding standard version 9 names those files; `fuzz_documents` fuzzes the five readers in CI and in the release checks; the three defects are fixed, each with a test that failed before the fix. Effectiveness checked at 2.1.0 |
| O-6 | Maintenance plan 6: trends | `tools/pr_trends.py`: the window of 2.0.0 (24 commits when measured, before this audit's reports) has 2 reports, 8.3 per 100 commits against an upper limit of 43.3; no root cause category has three reports in it. With this audit's three reports the window has five, still under its limit. The two windows above their limits are 0.3.0 and 0.4.0, explained in Chapter 40. | Observation | N-2 is the evaluation the plan asks for after MDQ-PR-071 |
| O-7 | SDP 7 and 10, CAPA procedure | `docs.anomalies` (76 reports, 2 open, each with a decision: MDQ-PR-006 and MDQ-PR-064, both decided again for this release by the release record), `docs.soup`, `docs.changes`, `docs.capa`: all pass. CAPA-0001 to CAPA-0004 are closed; CAPA-0005 is implemented and open until its effectiveness check. | Observation | The release record of 2.0.0 names CAPA-0005 |
| O-8 | Risk management: new functions reviewed against the hazards | CR-0029 adds RC-52 to H-06 (the product build cannot present simulated data as real); CR-0031 adds RC-53 and RC-54 to the time base; CR-0032 adds RC-55 of H-13 (no time of flight on an untrusted time base). `docs.risk`, `docs.threats` and the trace matrix pass. | Observation | None |

## Conclusion

Two minor nonconformities. The three breaking changes of the release were made under change
control but not recorded as implemented (N-1), corrected before the release checks. The readers
of files that MiniDAQ writes and reads again were not treated as readers of untrusted input
(N-2): three defects of that kind were found and fixed, and CAPA-0005 makes the rule and the
fuzzing cover those files. The step that rests on a person, the approval of the eight controlled
documents (O-4), was given under the software lead's standing delegation and is recorded after
the review of the release candidate, before the release checks.

## Document history

| Version | Change |
|---|---|
| 1 | First version, before the review of the release candidate and the release checks of 2.0.0. |
| 2 | O-4: the approvals recorded after the review was merged. |
