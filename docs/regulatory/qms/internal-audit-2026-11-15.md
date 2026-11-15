# Internal audit 2026-11-15: plan and practice before release 1.3.0

Version 3 (MiniDAQ 1.3.0-dev). Status: final.

| Field | Value |
|---|---|
| Scope | Design and development of MiniDAQ since release 1.2.0 (tag book-v1.2.0) up to the candidate of release 1.3.0: the two changes of the release (CR-0026, CR-0027) and their review, document control and approval, problem resolution, CAPA, the SOUP review and vulnerability triage, the release checks |
| Criteria | The [SDP](../sdp.md) version 16 (section 8, item 9: an internal audit before each minor release), the [CAPA procedure](../capa/README.md), the [change control procedure](../changes/README.md), and the clauses of ISO 13485:2016 that the [design file](design-file.md) maps |
| Method | Every commit since book-v1.2.0 against the commit policy (`tools/check_commits.py`); every controlled document against its version at release 1.2.0 (`tools/design_file.py --since book-v1.2.0`) and against the status a release requires; every CAPA; the tools of the `docs.*` tests run on the audited commit |
| Auditor | The book's author, as in the earlier audits: the same limit on independence applies |

It is held before the release checks of 1.3.0 that the release record cites, as SDP section 8,
item 9 asks.

## Findings

| ID | Requirement | What was found | Classification | Action |
|---|---|---|---|---|
| O-1 | SDP 5: every change reviewed, the review recorded in the commit | 9 commits since book-v1.2.0: `tools/check_commits.py . book-v1.2.0..HEAD` reports 0 problems under commit policy 2. | Observation | None |
| O-2 | ISO 13485 4.2.4: changes to documents identified | `tools/design_file.py . --check --since book-v1.2.0`: 20 clauses, 22 controlled documents, no controlled document changed without a new version. | Observation | None |
| O-3 | Change control procedure: a change approved before it is made | CR-0026 (time markers, register map 1.2) and CR-0027 (signed run records, calibration tables and reports) were approved before their commits, and each moved to "implemented" in a follow-up commit that names the implementing commit. Both approvals were given by the coordinator under the software lead's standing delegation of 2026-11-15; CR-0027's approval carried two conditions (no private key in the repository; negative tests for a changed file, a changed record, a wrong key and a missing signature), and `test_signing.cpp` and `test_signature.py` meet both: every key is made by the test in a temporary directory. | Observation | None |
| O-4 | ISO 13485 4.2.4: documents approved before issue | Five controlled documents said "draft for review": the SRS version 30, the ICD of the front-end boards version 3, the threat model version 15, the architecture version 22 and the SOUP list version 26. `tools/design_file.py` refuses a draft in a release, so the release cannot pass without their approval. | Observation | Approved for release 1.3.0 on 2026-11-15, given by the coordinator under the software lead's standing delegation, recorded as SRS version 31, ICD version 4, threat model version 16, architecture version 23 and SOUP list version 27, before the release checks |
| O-5 | SDP 7.3 and the SOUP list: known vulnerabilities assessed | The review for MiniDAQ 1.3 (SOUP list section 4, 2026-11-15) found no advisory for OpenSSL after those of 2026-11-10, none for nlohmann/json 3.12.0 or pybind11 3.1.0, and `tools/lock_audit.py` reports 0 vulnerabilities in the 30 locked Python packages. CR-0027 makes OpenSSL's Ed25519 and SHA-256 part of the server and the list tool; the SOUP list names both uses. | Observation | None |
| O-6 | Risk management: new functions reviewed against the hazards and threats | CR-0026 added a windowing failure mode for a marker that arrives too late to the sorter's FMEA and SRS-HW-017 to risk control RC-30; CR-0027 names its requirements in threats T-27 and T-54. `docs.threats`, `docs.risk` and the trace matrix pass. | Observation | None |
| O-7 | SDP 7 and 10, CAPA procedure | `docs.anomalies` (68 reports, 3 open, each with a decision; MDQ-PR-007 closed by CR-0026, MDQ-PR-006 decided again for this release), `docs.soup`, `docs.changes`, `docs.capa`: all pass. CAPA-0001 to CAPA-0004 are closed; no CAPA is open. | Observation | None |
| O-8 | SDP 6: static analysis on every change | The first run of `tools/static_analysis.sh` on CR-0027 reported two clang-tidy findings (a repeated branch body, a `reinterpret_cast` in the hashing of bytes); both were resolved before the commit, the cast with a scoped suppression that says why. The commit itself is clean. | Observation | None |
| O-9 | SDP 6: CI on every change; change control, impact analysis | After the audit's first version, CI's fuzz-smoke job failed on main: the decoder's fuzz target still counted a time marker as a single or an invalid crystal (MDQ-PR-069, a stale property, not a decoder defect). CR-0026's impact analysis had not named the fuzz target, and the local test run before a commit leaves out the fuzz label. Fixed in 4686729 with the crashing input kept as a seed, before the release checks were run again; the pre-commit hook's crash on that raw-bytes seed was fixed in the same commit. The release checks of 1.3.0 that had started on 9034920 were stopped, because their fuzzing would have failed on the same property. | Observation | The release checks run on the fixed commit. The impact analysis of a change to a decoder's counters names the fuzz target that states a property over them (MDQ-PR-069's root cause); no CAPA, because CI found it on the first push as designed |
| O-10 | SDP 6: performance regression gate before a release | The release checks on 895eaee passed parts 1 and 2 and failed part 3: the stream decoder was 16% slower than in 1.2.0 (MDQ-PR-070, introduced by CR-0026). CI's perf workflow had already failed on CR-0026's commit and was not read. Fixed and measured against 1.2.0 again (speed 0.973, within the gate) before the release checks were run again from the start. | Observation | Every workflow of a push is read, not only ci; the release checks run on the fixed commit |

## Conclusion

No nonconformity. CI found one stale test property after the first version (O-9) and the regression gate one slower decoder (O-10): both controls worked as designed, and both findings are fixed before the release. Both changes of the release went through change control with their approval
recorded before the work, and the condition attached to CR-0027 is met by its tests. The step that
rests on a person, the approval of the five controlled documents (O-4), was given before the
release checks under the software lead's standing delegation.

## Document history

| Version | Change |
|---|---|
| 1 | First version, before the release checks of 1.3.0. |
| 2 | O-9: MDQ-PR-069, found by CI after the first version, fixed before the release checks. |
| 3 | O-10: MDQ-PR-070, found by the release checks' regression gate, fixed before they were run again. |
