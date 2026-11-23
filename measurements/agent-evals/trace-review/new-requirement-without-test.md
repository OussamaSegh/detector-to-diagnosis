Trace review of the change. It adds one row to docs/regulatory/srs.md.

1. Requirement without a test: docs/regulatory/srs.md, line 108 of the changed file (the new row after SRS-PROC-001). The change adds `| SRS-SRT-999 | The sorter shall be fast. | sorter | T |`, which is to be verified by test (method T). No test names it. A repository-wide search for "SRT-999" finds only tools/gate_selftest.py:79-80. That file is a gate self-test fixture that injects this same row and expects tools/req_lint.py to report "SRS-SRT-999: vague word 'fast'". It is not a requirement test. docs/regulatory/trace-matrix.md has no row for SRS-SRT-999 either; its sorter rows run from SRS-SRT-001 to SRS-SRT-014 (lines 243-256). One-sentence fix: remove the row, or replace it with a measurable requirement and a `// REQ: SRS-SRT-999` test (and give it method M if it is a performance measure, as the SRS-PERF-02x rows are).

No other findings:
- 2 (test without a requirement): the change adds no test under minidaq/tests/, recon/tests/ or analysis/tests/.
- 3 (risk control without its verification): the change adds or changes no risk control. No control in docs/regulatory/risk/hazards.json names SRS-SRT-999. The sorter controls RC-03, RC-07, RC-16 and RC-17 (SRS-SRT-005, -007, -009, -010, -011) are untouched, and none of their tests or tags are removed.
- 4 (changed behavior without a changed requirement): the change touches no code. In particular it does not touch the class B sorter item (minidaq/include/minidaq/processing/coincidence_sorter, minidaq/src/processing/coincidence_sorter, from docs/architecture/software-items.json line 18).

Also noted (outside the four categories): tools/gate_selftest.py:79-80 shows that the repository's req_lint gate is built to reject this exact row for the vague word "fast". The new requirement also leaves out what it is measured against: a number, a unit and a reference machine.

What I read: docs/regulatory/srs.md (sections 2.6-2.7), docs/regulatory/trace-matrix.md (sorter rows), docs/regulatory/risk/hazards.json (the controls that name SRS-SRT IDs), docs/architecture/software-items.json (the sorter entry), and a repository-wide search for SRS-SRT-999.

What I could not check: I did not read tools/trace_matrix.py in full, so I judged tags against the convention given in the instructions. I ran no tools (req_lint, trace_matrix or the tests), so whether the gate fails on this change is inferred from the self-test fixture, not observed.
