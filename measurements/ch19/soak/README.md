# Soak test, Chapter 19 (SRS-SYS-003)

`tools/soak.py` for 30 minutes at 1,000,000 singles/s, sampling every 10 s, on the book's 4-vCPU
virtual machine, with the release programs built from commit 8284e0e. Files: `summary.txt` (the
tool's verdict) and `samples.csv` (every sample).

- Result: PASS. 1,800,032,317 singles (1,000,018/s), no loss, no fault, the run complete.
- Resident memory: 29.7 MiB at the start, 30.3 MiB at the end, 30.4 MiB at most; trend after the
  10-minute warm-up -0.006 MiB/h with a standard error of 0.033 MiB/h over 121 samples. The limit
  is 1 MiB/h.
- Latency (end to end, per 10 s interval): median of the interval p99 values 1.33 ms; 5 of the 181
  intervals had a p99 above 5 ms (at 610, 740, 1400, 1550 and 1710 s), the largest 16.2 ms with an
  interval maximum of 26.0 ms.

**Deviation.** The machine was not quiet: during the run, the exercises of Chapter 19 were
compiled and their tests run on the same 4 vCPUs. The latency outliers are not evidence about the
server, and the soak does not judge latency (its criteria are loss, faults, completeness and memory
growth). The latency requirements are measured on a quiet machine (Chapter 5,
`docs/performance-budget.md`); the soak of each release runs inside `tools/release_checks.sh`,
which runs nothing else at the same time.
