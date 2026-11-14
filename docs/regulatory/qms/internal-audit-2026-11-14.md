# Internal audit 2026-11-14: plan and practice before release 1.2.0

Version 2 (MiniDAQ 1.2.0-dev). Status: final.

| Field | Value |
|---|---|
| Scope | Design and development of MiniDAQ since release 1.1.0 (tag book-v1.1.0) up to the candidate of release 1.2.0: changes and their review, document control and approval, problem resolution, CAPA, SOUP review and vulnerability triage, the new release tools, the release checks |
| Criteria | The [SDP](../sdp.md) version 16 (section 8, item 9: an internal audit before each minor release), the [CAPA procedure](../capa/README.md), the [change control procedure](../changes/README.md), and the clauses of ISO 13485:2016 that the [design file](design-file.md) maps |
| Method | Every commit since book-v1.1.0 against the commit policy (`tools/check_commits.py`); every controlled document against its version at release 1.1.0 (`tools/design_file.py --since book-v1.1.0`) and against the status a release requires; every CAPA; the tools of the `docs.*` tests run on the audited commit |
| Auditor | The book's author, as in the earlier audits: the same limit on independence applies |

It is held before the release checks of 1.2.0 that the release record cites, as SDP section 8,
item 9 asks.

## Findings

| ID | Requirement | What was found | Classification | Action |
|---|---|---|---|---|
| O-1 | SDP 5: every change reviewed, the review recorded in the commit | 31 commits since book-v1.1.0: `tools/check_commits.py . book-v1.1.0..HEAD` reports 0 problems under commit policy 2. | Observation | None |
| O-2 | ISO 13485 4.2.4: changes to documents identified | `tools/design_file.py . --check --since book-v1.1.0`: no controlled document changed without a new version. | Observation | None |
| O-3 | ISO 13485 4.2.4: documents approved before issue | One controlled document says "draft for review": the SOUP list, version 24, the routine review for 1.2. It needs the software lead's approval before the release; `tools/design_file.py` refuses a draft in a release, so the release cannot pass without it. | Observation | Approved by the software lead on 2026-11-14, recorded as SOUP list version 25, before the release checks |
| O-4 | SDP 7.3 and the SOUP list: known vulnerabilities assessed | The vulnerability scan of CI turned red on 2026-11-14 on five OpenSSL advisories of 2026-11-10. Each is triaged `not_affected` (`code_not_reachable`) in `vulnerability-triage.json`: the affected code (QUIC, AES-GCM-SIV, CMS) is not used by MiniDAQ. The gate did what it is there for: a new advisory stopped CI until a person decided. | Observation | None |
| O-5 | SDP 6: CI on every change | The web edition's check failed in the Pages workflow on the branch (1221 anchors reported as unresolved: the check compared relative with absolute paths). The deploy step did not run, so nothing was published from the branch; it was fixed, with a test, before the merge. A new CI job builds and tests on arm64. | Observation | None |
| O-6 | Product verification of the book | Two defects of the EPUB of 1.1.0 were found by reading it, not by EPUBCheck, which passed it: a wrongly decoded copyright sign on the title page (E-007, a locale left unset in the build) and an appendix numbered as a chapter (E-008). Both are fixed and recorded in the new errata (`book/errata.json`, checked by `book.errata`). The new cross-reference check (`book.xrefs`) found five exercises marked "(S)", a mark the book does not define (E-006). | Observation | None |
| O-7 | SDP 7 and 10, CAPA procedure | `docs.anomalies` (68 reports, 4 open, each with a decision), `docs.soup`, `docs.changes`, `docs.capa`: all pass. CAPA-0001 to CAPA-0004 are closed; no CAPA is open. | Observation | None |
| O-8 | SDP 8: release steps | The release steps that rested on memory now have tools: `tools/release_checks.sh` resumes the parts not yet recorded as passed, `tools/release_record.py` writes the record's skeleton from the evidence and refuses a record with a `TODO(record)` line left, and `tools/post_release.py` sets the version of every package (`docs.package_versions`). They are used for the first time in this release; the record says so. | Observation | None |

## Conclusion

No nonconformity. The controls that CAPA-0002 put in tools held for every change since 1.1.0,
and the vulnerability gate stopped CI on new advisories until they were assessed. The one step that
rests on a person, the software lead's approval of the SOUP list (O-3), was given before the
release checks.

## Document history

| Version | Change |
|---|---|
| 1 | First version, before the release checks of 1.2.0. |
| 2 | O-3: the software lead's approval of the SOUP list, given 2026-11-14. |
