# MiniDAQ 1.0 acceptance specification, version 1: NOT ACCEPTED

Candidate commit `cfb708fb44b2`; evidence from `measurements/release-0.7.0`.

| Criterion | Requirements | Target | Found | Verdict |
|---|---|---|---|---|
| ACC-01: The acquisition pipeline's throughput, with the coincidence sorter, in the hardened build | SRS-PERF-020 | median of 5 repetitions at least 20 M singles/s (10 M required, a margin of 2) | median 37.5 M singles/s | PASS |
| ACC-02: The list-mode writer's throughput with fsync at close | SRS-PERF-021 | the slowest of 3 runs at least 3 M coincidences/s | slowest 12.01 M coincidences/s of 3 | PASS |
| ACC-03: A long acquisition at the reference rate | SRS-SYS-003 | 30 minutes at 1 M singles/s: no loss, no fault, complete, memory growth within 1 MiB/h | 1e+06 singles/s for 30 min, PASS | PASS |
| ACC-04: End-to-end latency at the reference rate | SRS-PERF-022 | the 99th percentile of every 10 s interval of the soak at most 10 ms | p99 at most 4.42 ms | PASS |
| ACC-05: The chain end to end: the server's records against the offline reference, every count balanced between the stages, the daily QC | SRS-SYS-006, SRS-SYS-007, SRS-ANA-005 | every check of both acquisitions of tools/e2e.py passes, the records equal to the reference's | e2e/e2e.json does not exist | MISSING |
| ACC-06: The image at the end of the chain | SRS-SYS-008 | the phantom's radius at half level within 2 mm of 80 mm, center over periphery within 10% of 1 | e2e/e2e.json does not exist | MISSING |
| ACC-07: The system test plan, executed on the release build | SRS-SYS-001, SRS-SYS-002, SRS-SYS-004, SRS-SYS-005 | every test case passed, none skipped | 34 test cases: 34 passed, 0 failed, 0 skipped | PASS |
| ACC-08: Every verification of a release (SDP section 6) that the release checks run | (process) | all four parts end with 'all release checks passed', on the commit of part 1 | parts passed: 1, 2, 3, 4 of 1, 2, 3, 4 | PASS |
| ACC-09: Every requirement verified, every hazard closed or justified, every anomaly evaluated, the requirements frozen or changed under change control | (process) | the checks docs.trace, docs.risk, docs.anomalies and docs.baseline pass on the commit | the repository is at 2554964ba6ab, not at the candidate | STALE |

6 pass, 0 fail, 2 missing, 1 stale.
