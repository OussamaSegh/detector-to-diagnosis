# Internal audit 2026-11-24: plan and practice before release 2.2.0

Version 2 (MiniDAQ 2.2.0-dev). Status: final, accepted by the software lead in writing on
2026-11-24 at 08:25 UTC.

| Field | Value |
|---|---|
| Scope | Design and development of MiniDAQ since release 2.1.0 (tag book-v2.1.0) up to the candidate of release 2.2.0: the two changes of the release (CR-0036 and CR-0037), problem resolution (MDQ-PR-088 to MDQ-PR-095), the CAPA evaluation of MDQ-PR-081, MDQ-PR-087 and MDQ-PR-089 that the roadmap asks for, CAPA-0006's effectiveness, the SOUP review, document control and approval, and the CI of `main` |
| Criteria | The [SDP](../sdp.md) version 22 (section 8, item 9: an internal audit before each minor or major release; section 5: before and after a push), the [maintenance plan](../maintenance-plan.md) version 4 (section 6, trends), the [CAPA procedure](../capa/README.md), the [change control procedure](../changes/README.md), the [roadmap of 2.2.0](../../ROADMAP-2.2.0.md) (Theme R's exit), and the clauses of ISO 13485:2016 that the [design file](design-file.md) maps |
| Method | Every commit since book-v2.1.0 against the commit policy (`tools/check_commits.py`); every controlled document against its version at release 2.1.0 (`tools/design_file.py --check --since book-v2.1.0`) and against the status a release requires; every change request's status against its commits; every CAPA (`tools/check_capa.py`); `tools/pr_trends.py` for the window of 2.2.0; the CI runs of `main` since book-v2.1.0, read with the GitHub API for each commit; the tools of the `docs.*` tests run on the audited tree |
| Auditor | The assistant that wrote most of the window's commits, for the book's author: the limit on independence of the earlier audits applies, and more strongly. The software lead's acceptance of this audit is the review of it. |

It is held before the release checks of 2.2.0 that the release record cites, as SDP section 8,
item 9 asks.

## Findings

| ID | Requirement | What was found | Classification | Action |
|---|---|---|---|---|
| O-1 | SDP 5: every change reviewed, the review recorded in the commit | 19 commits since book-v2.1.0 before this audit's own: `tools/check_commits.py . book-v2.1.0..HEAD` reports 0 problems under commit policy 3. Three carry the optional `Gate:` trailer; two of them say FAIL, each with the items the gate left to a person named and reviewed in the message. | Observation | None |
| O-2 | SDP 5, before and after a push; SDP 8: a green CI before a tag | `ci` failed on five of the 19 commits: ee34473, c98f417, 6fe8a40, ac7f3bc and ddc8d5a. Each was read before the next push and reported the same day (MDQ-PR-091 to MDQ-PR-095), and only its fix was pushed after it. Three causes were ones no local check reproduced: a CI machine without git-clang-format (MDQ-PR-093), static analysis, which the unit suite does not run (MDQ-PR-094), and a test of scheduling that a loaded runner failed after an idle machine passed it (MDQ-PR-095, the second report of that test after MDQ-PR-086). | Observation | CAPA-0006 effective (O-6); SDP version 23 adds static analysis before a push of C++ code |
| O-3 | ISO 13485 4.2.4: changes to documents identified | `tools/design_file.py . --check --since book-v2.1.0`: 20 clauses, 25 controlled documents, no controlled document changed without a new version. | Observation | None |
| O-4 | ISO 13485 4.2.4: documents approved before issue | Six controlled documents are drafts: the SDP version 23, the SRS version 39, the SOUP list version 32, the architecture version 29, the performance budget version 5 and the threat model version 19. The approvals of controlled documents are the software lead's own, in writing. | Observation | The software lead's written approval of the six before the release checks |
| N-1 | ISO 13485 4.2.5 and 8.2.4: records of audits kept and indexed | The audit of 2026-11-23, before release 2.1.0, is not in the design file: neither among the controlled documents nor in clause 8.2.4's evidence. `docs.design_file` passed because it checks what the index lists, not what it omits. | Minor nonconformity | Corrected with this audit: both audits are indexed. No CAPA: the check lists the earlier audits, and this audit's method reads the index against the folder |
| O-5 | Change control procedure | CR-0036 (the agent gate and the agent files) and CR-0037 (several nodes in the simulator) were approved by the software lead in writing on 2026-11-23 before their commits of record; CR-0037 is implemented with its notes (the merge in the source stage's thread, the pipeline item unchanged). CR-0036 is implemented but for one part: the agent's own files (`CLAUDE.md`, `.claude/`) are drafts outside the repository, because committing the settings turns the hooks on for every later session, and that step waits for the software lead's explicit words. `docs.changes` passes. | Observation | The agent files committed when the software lead says so, or CR-0036's remaining part moved to 2.3.0 in the release record |
| O-6 | CAPA procedure: effectiveness checked when due | CAPA-0006 is due at 2.2.0. Its criteria hold (O-2 and the `Tests:` trailers of all 19 commits): **effective**, closed. | Observation | None |
| O-7 | Roadmap 2.2.0, Theme R: the CAPA evaluation of MDQ-PR-081, MDQ-PR-087 and MDQ-PR-089 | The three share a cause: a fact of the release checks written in each script and tool that uses it, changed where its author looked. A search found the soak's length, the presets, the fuzz targets and their seconds each in two or three places. | Observation | CAPA-0007 opened and implemented: `tools/release_facts.json`, read by `tools/release_checks.sh`, `ci/run_all.sh` and `tools/release_record.py`, with a test that fails on a copy; effectiveness at 2.3.0 |
| O-8 | SDP 7, maintenance plan 6: problem resolution and trends | `tools/pr_trends.py`: the window of 2.2.0 has 8 reports in 20 commits, 40.0 per 100 against an upper limit of 47.6, no signal. The category "process" has three (MDQ-PR-089, MDQ-PR-092, MDQ-PR-094); evaluated: MDQ-PR-089 joins CAPA-0007, MDQ-PR-092 and MDQ-PR-094 are in CAPA-0006's source and addressed by its rule and the SDP's version 23. MDQ-PR-095 repeats MDQ-PR-086's cause in the same test (a test of scheduling given too few chances); two reports with one cause would open a CAPA, but both are this one test, the second fix replaces a count with a time margin, and CAPA-0001's rule (a wait states its reason, `tests.waits`) already covers the others. Evaluated: no CAPA; a third report of a scheduling test reopens the question. Every report of the window is closed with its root cause. | Observation | None further |
| O-9 | SDP 7.3, the SOUP list: known vulnerabilities assessed | The review of 2026-11-23 for MiniDAQ 2.2 (SOUP list version 32, section 4) keeps every item; Theme P and Theme S add no SOUP. The review asks that the trackers and advisories be read again before release 2.2.0, the four OpenSSL records known only from secondary sources among them. | Observation | The SOUP review is repeated before the release checks |
| O-10 | Risk management: new functions reviewed against the hazards | CR-0037 adds a cause to H-01 and RC-56 (the node merge's waiting rule and the single-node oracle); the threat model's version 19 reviews an agent with shell access. `docs.risk`, `docs.threats` and the trace matrix (274 requirements) pass. | Observation | None |

## Conclusion

One minor nonconformity, corrected with this audit: the audit before release 2.1.0 was not in
the design file (N-1). CAPA-0006 is effective and closed; CAPA-0007 removes the cause shared by
three problem reports of the release records. The steps that rest on a person are the software
lead's acceptance of this audit, the written approval of the six draft documents (O-4), and the
decision on the agent files of CR-0036 (O-5).

## Document history

| Version | Change |
|---|---|
| 1 | First version, before the release checks of 2.2.0. |
| 2 | Accepted by the software lead (the book's author) in writing on 2026-11-24, with the approvals of release 2.2.0; the findings do not change. |
