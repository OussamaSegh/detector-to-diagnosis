# Internal audit 2026-11-23: plan and practice before release 2.1.0

Version 2 (MiniDAQ 2.1.0-dev). Status: final.

| Field | Value |
|---|---|
| Scope | Design and development of MiniDAQ since release 2.0.1 (tag book-v2.0.1) up to the candidate of release 2.1.0: the two changes of the release (CR-0034 and CR-0035), problem resolution (MDQ-PR-083 to MDQ-PR-085, the closure of MDQ-PR-064), CAPA-0005's effectiveness, the SOUP review, document control and approval, and the CI of `main` |
| Criteria | The [SDP](../sdp.md) version 22 draft (section 8, item 9: an internal audit before each minor or major release), the [maintenance plan](../maintenance-plan.md) version 4 (section 6, trends), the [CAPA procedure](../capa/README.md), the [change control procedure](../changes/README.md), the [coding standard](../../coding-standard.md) rule 3, and the clauses of ISO 13485:2016 that the [design file](design-file.md) maps |
| Method | Every commit since book-v2.0.1 against the commit policy (`tools/check_commits.py`); every controlled document against its version at release 2.0.1 (`tools/design_file.py --check --since book-v2.0.1`) and against the status a release requires; every change request's status against its commits; every CAPA; `tools/pr_trends.py` for the window of 2.1.0; the CI runs of `main` since book-v2.0.1, read with the GitHub API; the tools of the `docs.*` tests run on the audited commit |
| Auditor | The book's author, as in the earlier audits: the same limit on independence applies |

It is held before the release checks of 2.1.0 that the release record cites, as SDP section 8,
item 9 asks.

## Findings

| ID | Requirement | What was found | Classification | Action |
|---|---|---|---|---|
| O-1 | SDP 5: every change reviewed, the review recorded in the commit | 35 commits since book-v2.0.1 before this audit's own: `tools/check_commits.py . book-v2.0.1..HEAD` reports 0 problems under commit policy 2. | Observation | None |
| N-1 | SDP 8: tag only after CI on the release commit is green; ISO 13485 7.3.6: verification results recorded and acted on | Every CI run on `main` from 9a92709 (2026-11-17) to 13bfdb3 (2026-11-22), about 30 commits, failed, and no record noticed it: `tests.waits` on Exercise 29.4's test in the seven build-test jobs, and from 2026-11-18 `vulnerability-scan` on eight new OpenSSL findings without a triage decision. The commits had been pushed after subsets of the unit suite. No release was made from a red commit, and the eight findings are in features MiniDAQ does not use. | Minor nonconformity | MDQ-PR-085; corrected in 6162e1e; CAPA-0006 (SDP version 22, section 5: the whole unit suite before a push, the CI result read after it). Effectiveness checked at 2.2.0 |
| O-2 | ISO 13485 4.2.4: changes to documents identified | `tools/design_file.py . --check --since book-v2.0.1`: 20 clauses, 25 controlled documents, no controlled document changed without a new version. | Observation | None |
| O-3 | ISO 13485 4.2.4: documents approved before issue | Five controlled documents are drafts: the SDP version 22, the SRS version 38, the SOUP list version 31, the system test plan version 6 and the coding standard version 11. Since the release of 2.0.1 the approvals of controlled documents are the software lead's own, in writing, and not the coordinator's under delegation. | Observation | The software lead's written approval of the five is asked before the release checks |
| O-4 | Change control procedure | CR-0034 (the projector's `out`) and CR-0035 (the release soak of 100 minutes) were each approved by the software lead in writing before their commits and moved to "implemented" with their commits and tests; `docs.changes` passes. CR-0035's approval was given in a message, because the decision card recorded the option the user did not mean; the message is the record. | Observation | None |
| O-5 | SDP 7, maintenance plan 6: problem resolution and trends | `tools/pr_trends.py`: the window of 2.1.0 (36 commits) has 5 reports, 13.9 per 100 commits against an upper limit of 38.5; no root cause category has three reports in it. MDQ-PR-064 is closed by CR-0035 with its root cause; MDQ-PR-006 stays open with its decision. MDQ-PR-084 (validation with `^...$`) is the first report of its kind; the coding standard gains rule 3.6 for it (version 11), as an improvement, without a CAPA. | Observation | Coding standard rule 3.6 |
| O-6 | SDP 7.3, the SOUP list: known vulnerabilities assessed | The review of 2026-11-23 (SOUP list section 4): nlohmann/json and pybind11 unchanged, the Python lock without a known vulnerability, eight OpenSSL findings (the advisory of 2026-11-17 and five records of 2026-11-18) in functions and protocols MiniDAQ does not use, each with a decision. Four are known only from secondary sources and are to be read again in Ubuntu's notice. | Observation | None further |
| O-7 | CAPA procedure: effectiveness checked when due | CAPA-0005 is due at 2.1.0. Its first criterion holds: `fuzz-smoke` runs `fuzz_documents` on every push and passed on 13bfdb3. Its third holds: none of MDQ-PR-077 to MDQ-PR-085 has the cause "a field of a file MiniDAQ reads was read without checking its type". Its second, ten minutes of `fuzz_documents` without a crash in the release checks of 2.1.0, is still to run. | Observation | The release record completes CAPA-0005's check from the release checks |
| O-8 | Maintenance plan 6: a root cause category with three reports in one window is evaluated for a CAPA | Added after the release checks. Writing the release record found MDQ-PR-087 (the skeleton's soak row still said 30 minutes after CR-0035), the third report of the category "tool" in the window of 2.1.0, with MDQ-PR-082 and MDQ-PR-083. The three causes differ: a summary that did not name the failed part, a parser that read one line at a time, a length written in two places. MDQ-PR-087's cause is that of MDQ-PR-081 (a change to what the checks do, made in the checks but not in the record's generator); MDQ-PR-081 reached 2.0.1, MDQ-PR-087 was found before a record used it. `tools/pr_trends.py` after it: 7 reports in 39 commits, 17.9 per 100 against a limit of 38.2. Evaluated: no CAPA. No common cause joins the three, the rate is within its limit, and the repeated cause is closed where it occurs: a test now reads the soak's length from `tools/release_checks.sh` and fails a skeleton that names another. | Observation | MDQ-PR-087; evaluated again at 2.2.0 with that window's trend |

## Conclusion

One minor nonconformity: the CI of `main` was red for six days without a record noticing (N-1).
It was corrected before the release checks, and CAPA-0006 adds the rule the SDP lacked. The
steps that rest on a person are the software lead's written approval of the five draft
documents (O-3) and, after the release checks, CAPA-0005's effectiveness (O-7).

## Document history

| Version | Change |
|---|---|
| 1 | First version, before the release checks of 2.1.0. |
| 2 | O-8: the trend evaluation after MDQ-PR-087, found while the release record was written. |
