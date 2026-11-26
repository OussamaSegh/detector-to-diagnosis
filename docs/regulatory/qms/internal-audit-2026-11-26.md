# Internal audit 2026-11-26: plan and practice before release 2.3.0

Version 1 (MiniDAQ 2.3.0-dev). Status: final, accepted by the coordinator under the software lead's standing delegation, in writing on 2026-11-26 at 07:33 UTC.

| Field | Value |
|---|---|
| Scope | Design and development of MiniDAQ since release 2.2.0 (tag book-v2.2.0) up to the candidate of release 2.3.0: the changes of the release (CR-0038, CR-0039; CR-0040 approved for 3.0.0), problem resolution (MDQ-PR-099 to MDQ-PR-105), CAPA-0007's effectiveness, the SOUP review, document control and approval, the CI of `main`, and the privacy rule on committed evidence |
| Criteria | The [SDP](../sdp.md) version 25 (section 8, item 9: an internal audit before each minor or major release; section 5: before and after a push), the [maintenance plan](../maintenance-plan.md) version 4 (section 6, trends), the [CAPA procedure](../capa/README.md), the [change control procedure](../changes/README.md), the [roadmap of 2.3.0](../../ROADMAP-2.3.0.md), the privacy rule of `CLAUDE.md`, and the clauses of ISO 13485:2016 that the [design file](design-file.md) maps |
| Method | Every commit since book-v2.2.0 against the commit policy (`tools/check_commits.py`); every controlled document against its version at release 2.2.0 (`tools/design_file.py --check --since book-v2.2.0`) and the status a release requires; every change request's status against its commits; every CAPA (`tools/check_capa.py`); `tools/pr_trends.py` for the window of 2.3.0; the failed CI runs of `main` since book-v2.2.0, read with the GitHub API; a search of every tracked file under `measurements/` and `docs/` for a path of a home or scratch directory |
| Auditor | The assistant that wrote most of the window's commits, for the book's author: the limit on independence of the earlier audits applies. The software lead's acceptance of this audit is the review of it. |

It is held before the release checks of 2.3.0 that the release record cites, as SDP section 8,
item 9 asks.

## Findings

| ID | Requirement | What was found | Classification | Action |
|---|---|---|---|---|
| O-1 | SDP 5: every change reviewed, the review recorded in the commit | 40 commits since book-v2.2.0 before this audit's own: `tools/check_commits.py . book-v2.2.0..HEAD` reports 0 problems under commit policy 3. Nine carry the optional `Gate:` trailer; three say FAIL on the gate's own check, each because the commit changed a check the gate runs, which the message names for a person. | Observation | None |
| O-2 | SDP 5, before and after a push; SDP 8: a green CI before a tag | `ci` failed on one commit of `main` in the window, 773ef25 (Exercise 29.4's test, MDQ-PR-105). It was read before the next push and fixed alone in b2cd12b, green; every later commit of `main` is green, up to 396a6ab. | Observation | None |
| O-3 | ISO 13485 4.2.4: changes to documents identified | `tools/design_file.py . --check --since book-v2.2.0`: 20 clauses, 29 controlled documents, no controlled document changed without a new version. | Observation | None |
| O-4 | ISO 13485 4.2.4: documents approved before issue | Drafts at the audit: the SDP version 25, the system test plan version 7, the SOUP list version 33 and the acceptance specification version 3 (`verification/acceptance.json`); the release-checks skill goes to version 2 with CAPA-0008. Approvals are given by the coordinator under the software lead's standing delegation. | Observation | Their approval before the release checks |
| N-1 | `CLAUDE.md`, privacy: no absolute path of the machine in a committed file | 668 lines in 184 files under `measurements/` named a home directory or an agent's scratch directory, in the evidence of every release from 0.3.0 to 2.2.0 (MDQ-PR-106). MDQ-PR-101 and MDQ-PR-103 had each corrected one writer; the rule was checked on agent files only. | Minor nonconformity | Corrected; CAPA-0008: `tools/evidence_paths.py` (TL-53), `docs.evidence_paths` in the unit suite, the release-checks skill fixes a release's evidence; effectiveness at 3.0.0 |
| O-5 | Change control procedure | CR-0038 (the A/B soak, ACC-10) and CR-0039 (photos and their check) were approved before their commits of record and are implemented; CR-0039's temporary photos-inbox branch is deleted and recorded. CR-0040 (optional CUDA, OpenMP and PyTorch) is approved for 3.0.0 and changes nothing in 2.3.0. `docs.changes` passes. | Observation | None |
| O-6 | CAPA procedure: effectiveness checked when due | CAPA-0007 is due at 2.3.0. Its criterion has three parts: the release checks of 2.2.0 and 2.3.0 run from `tools/release_facts.json`; their records pass `release_record.py check` with no row edited by hand; no problem report until 2.3.0 with the cause "a fact of the release checks changed in one place and not another". The checks of 2.2.0 ran from the file, and its record passed the check (its deviation rows through MDQ-PR-098's rule, not by hand). CR-0038 added the soak's blocks to the same file, read by `tools/release_checks.sh`. No report of the window has that cause. | Observation | The part on 2.3.0's checks is judged in its release record, which closes CAPA-0007 if it holds |
| O-7 | SDP 7, maintenance plan 6: problem resolution and trends | `tools/pr_trends.py`: the window has 8 reports (with MDQ-PR-106) in 41 commits, 19.5 per 100 against an upper limit of 39.6, no signal. By cause: five "tool", two "process", one "test". Evaluated: MDQ-PR-101 and MDQ-PR-103 share a cause and with MDQ-PR-106 open CAPA-0008 (N-1). MDQ-PR-100 (a push the hook allowed), MDQ-PR-102 (the edit hook formatted a whole file) and MDQ-PR-104 (a test folder the change check did not read) have three different causes, each fixed with a test that fails without the fix: no CAPA. MDQ-PR-099 (a deviation with no path in the plan) is answered by SDP version 24 and 25. | Observation | None further |
| O-8 | The audit of 2.2.0 (its O-8): a third report of a scheduling test reopens the question | MDQ-PR-105 is the third report of Exercise 29.4's thread test, after MDQ-PR-086 and MDQ-PR-095. Its cause was measured: the test's window lay where the solution holds the lock in a debug build, not in the scheduler; the first two reports read the same failure as scheduling and gave more attempts. The cause is fixed and the test now passes with checks three times as long. The lesson is in MDQ-PR-105's record: a timing test that fails is measured before it is given more time. | Observation | No CAPA: one test, its cause found and removed; a fourth report of a timing test that was given more attempts instead of a measurement opens one |
| O-9 | SDP 7.3, the SOUP list: known vulnerabilities assessed | The review of 2026-11-24 for MiniDAQ 2.3 (SOUP list version 33) keeps every item; the window adds no SOUP to the product (CR-0040's packages are optional and come with 3.0.0). The CI's vulnerability scan passed on every push of the window. | Observation | None |
| O-10 | Roadmap 2.3.0, Theme I: photos under the photo policy | The book's two photos are CC0, read from each file page's license metadata through the Commons API by the photo job (`book/figures/photos/credits.json`); the policy asks that a person read the license page, which the session's network does not reach. | Observation | The author reads the two pages before 3.0.0, the edition offered for sale; the record of 2.3.0 says so |
| O-11 | Risk management: new functions reviewed against the hazards | The window changes no product code: tools, tests, the book and its figures. `docs.risk`, `docs.threats` and the trace matrix pass. | Observation | None |

## Conclusion

One minor nonconformity, corrected with this audit: committed evidence named paths of the
machines that wrote it (N-1, MDQ-PR-106), with CAPA-0008 to keep them out. CAPA-0007's last
part is judged with the release checks of 2.3.0. The steps that rest on a person are the
approval of the four draft documents and the skill (O-4), this audit's acceptance, and the
author's reading of the two photos' license pages before 3.0.0 (O-10).

## Document history

| Version | Change |
|---|---|
| 1 | First version, before the release checks of 2.3.0; accepted with the approvals of release 2.3.0. |
