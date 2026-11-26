# MiniDAQ 1.0 acceptance specification, version 3: NOT ACCEPTED

Candidate commit `1926017dc0ac`; evidence from `measurements/release-2.3.0`.

| Criterion | Requirements | Target | Found | Verdict |
|---|---|---|---|---|
| ACC-01: The acquisition pipeline's throughput, with the coincidence sorter, in the hardened build | SRS-PERF-020 | median of 5 repetitions at least 20 M singles/s (10 M required, a margin of 2) | median 34.6 M singles/s | PASS |
| ACC-02: The list-mode writer's throughput with fsync at close | SRS-PERF-021 | the slowest of 3 runs at least 3 M coincidences/s | slowest 17.99 M coincidences/s of 3 | PASS |
| ACC-03: A long acquisition at the reference rate | SRS-SYS-003 | 100 minutes (30 until 2.1.0, CR-0035) at 1 M singles/s, in 5 blocks of 20 minutes interleaved with the previous release's since 2.3.0 (CR-0038): no loss, no fault, complete, memory growth within 1 MiB/h (the slope pooled within the blocks) | 1e+06 singles/s for 100 min, PASS | PASS |
| ACC-04: End-to-end latency at the reference rate | SRS-PERF-022 | the 99th percentile of at least 99% of the 100-minute soak's 600 intervals of 10 s at most 10 ms (every interval until version 2, CR-0025; 180 intervals until 2.1.0, CR-0035; in 5 blocks of 20 minutes since 2.3.0, CR-0038). Absolute: the comparison with the previous release (ACC-10) never replaces it | p99 at most 10 ms in 592 of 600 intervals (98.7%, 99% required); highest 26.08 ms | FAIL |
| ACC-05: The chain end to end: the server's records against the offline reference, every count balanced between the stages, the daily QC | SRS-SYS-006, SRS-SYS-007, SRS-ANA-005 | every check of both acquisitions of tools/e2e.py passes, the records equal to the reference's | 33 of 33 checks pass, records equal to the reference in 2 of 2 acquisitions | PASS |
| ACC-06: The image at the end of the chain | SRS-SYS-008 | the phantom's radius at half level within 2 mm of 80 mm, center over periphery within 10% of 1 | radius 80.25 mm, center over periphery 1.0419 | PASS |
| ACC-07: The system test plan, executed on the release build | SRS-SYS-001, SRS-SYS-002, SRS-SYS-004, SRS-SYS-005 | every test case passed, none skipped | 38 test cases: 38 passed, 0 failed, 0 skipped | PASS |
| ACC-08: Every verification of a release (SDP section 6) that the release checks run | (process) | all five parts end with 'all release checks passed', on the commit of part 1 (four parts until 2.2.0; the soak is part 5 since CR-0038) | parts passed: 1, 2, 3, 4, 5 of 1, 2, 3, 4, 5 | PASS |
| ACC-09: Every requirement verified, every hazard closed or justified, every anomaly evaluated, the requirements frozen or changed under change control | (process) | the checks docs.trace, docs.risk, docs.anomalies and docs.baseline pass on the commit | all pass | PASS |
| ACC-10: End-to-end latency against the previous release on the same machine | SRS-PERF-022 | the candidate's count of soak intervals above 10 ms not higher than the previous release's, its soak interleaved with the candidate's in blocks: Fisher's exact test, one-sided, p at least 0.05 (CR-0038). It says whether a failure of ACC-04 is in the code or in the machine; it does not meet SRS-PERF-022 | candidate 8 of 600, previous release 10 of 600; one-sided p 0.7613 | PASS |

9 pass, 1 fail, 0 missing, 0 stale.
