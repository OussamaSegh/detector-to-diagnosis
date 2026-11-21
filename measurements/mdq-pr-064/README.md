# MDQ-PR-064: measured soaks

Soaks with the finer measure of the review of 2.0.0 (`tools/soak.py`: per second, the steal time
and the largest run-queue wait of one server thread), run to catch a latency peak with the
measure beside it.

`soak-100min/`: `tools/soak.py build/release/minidaq/apps OUT --minutes 100` on 2026-11-16,
18:46 to 20:27 UTC, at 63661d4 (the programs of 2.0.0 but for MDQ-PR-078, which the server does
not use), the `release` preset, a 4-CPU virtual machine, nothing else running.

- 600 intervals of 10 s; none had a 99th percentile above 10 ms. The highest was 8.16 ms, at
  840 s, when the largest one-second wait was 32.4 ms (`mdq-decode`) and the one-second steal
  1.47%.
- The largest one-second run-queue wait of one thread: median 18.0 ms, max 99.6 ms. Its
  correlation with the interval's 99th percentile is 0.14 (0.13 in the review's 30-minute run).
- Steal over each interval: max 0.68%; per second, max 4.03%.
- 6.0 billion singles, no loss, resident memory flat (+0.000 MiB/h).

With the 30-minute run of the review, 780 intervals at 2.0.0's code have had no peak. The release
checks' soaks had peaks in 0.8.0, 0.9.0, 1.0.0 (2 of 180) and 1.1.0 (1 of 180), and none in
1.2.0, 1.3.0 and 2.0.0 (0 of 180 each): 1,320 intervals without a peak since 1.2.0. The report
stays open (roadmap 2.1.0, theme I) until a peak is caught
with the measure or the rate is judged with longer evidence.

`unpinned-100min/`: the same command on 2026-11-21, 20:06 to 21:46 UTC, at c7d72d7 (the programs
of 2.0.1: no file of `minidaq/src`, `apps` or `include` has changed since), the `release`
preset, the same 4-CPU virtual machine, nothing else running.

- 2 of 600 intervals had a 99th percentile above 10 ms: 18.09 ms at 2650 s and 13.57 ms at
  3010 s (99.67% within the limit; SRS-PERF-022 asks for 99%). The result is PASS.
- In both, the largest one-second run-queue wait of one thread was `mdq-sort`'s, 24.1 and
  25.9 ms, and the one-second steal 1.73% and 0.60%. Neither stands out: over the run the
  largest wait had a median of 26.3 ms and a maximum of 89.8 ms (at 2000 s, `mdq-decode`, an
  interval whose 99th percentile was below the limit), and 98% of the intervals had a wait of
  24 ms or more.
- The correlation of the interval's 99th percentile with the largest wait is 0.04, with the
  one-second steal 0.14.
- 6.0 billion singles, no loss, resident memory flat (+0.001 MiB/h).

So the peak has now been caught with the measure beside it, and the measure does not explain it:
neither the run-queue wait of a server thread nor the steal time was larger in the two intervals
than in the 598 others. Waiting for a CPU, as these counters see it, is not the cause. A pinned
soak follows, to test the next candidate, the threads' movement between CPUs.

`pinned-100min/`: the same command on 2026-11-21, about 21:58 to 23:38 UTC, at 611e86c (the same
programs), with `pin.sh` beside it, which every 5 s pins the server's pipeline threads by name:
`mdq-source` to CPU 0, `mdq-decode` to 1, `mdq-sort` to 2, `mdq-pair` and `mdq-write` to 3. The
simulator, the client and the server's other threads were not pinned. Four CPUs do not give five
threads one each, so `mdq-pair` and `mdq-write` shared one.

- 9 of 600 intervals had a 99th percentile above 10 ms, up to 98.04 ms at 1300 s (98.5% within
  the limit). The soak's other results: 6.0 billion singles, no loss, memory flat, PASS (the soak
  checks no latency; ACC-04 is evaluated from it at a release).
- `mdq-write`, sharing CPU 3 with `mdq-pair`, had the largest wait in 597 of 600 seconds sampled,
  with a median of 125 ms per second against 26 ms unpinned. In the nine intervals its wait was
  123 to 156 ms: the same as in the other 591. The correlation of the 99th percentile with the
  largest wait is 0.13, with the one-second steal 0.23; the worst interval had the run's
  second-highest one-second steal, 4.52% (the highest, 10.34%, fell in an interval within the
  limit).

## What the three runs say

1. **Waiting for a CPU, as the guest sees it, does not mark the peaks.** In neither run were the
   peaks' intervals different from the others in run-queue wait, and steal was at most weakly
   related to them (0.14 and 0.23).
2. **Pinning makes it worse, not better.** Fixing the threads to CPUs raised the rate from 2 in
   600 to 9 in 600 and the worst interval from 18 to 98 ms. With five busy pipeline threads, a
   simulator and a client on four CPUs, the scheduler's freedom to move a thread to an idle CPU is
   worth more than the caches a pinned thread keeps. A setting for the threads' CPU affinity
   (roadmap 2.1.0, Theme I) is therefore not added: the measurement does not show MiniDAQ's own
   scheduling as the cause, and the one placement four CPUs allow is worse than the default.
3. **The peaks are rare.** With the programs of 2.0.x and the default scheduling, 2 of 1,740
   intervals have had a peak (the review's 180, the 600 of 2026-11-16, the release soaks of 2.0.0
   and 2.0.1, 180 each, and the 600 above): 0.11%, at most 0.36% at 95% confidence
   (Clopper-Pearson), against the 1% that SRS-PERF-022 allows. No single was lost in any of them.
4. **A 30-minute soak judges that rate badly.** ACC-04 allows one peak in 180 intervals. At a rate
   of 0.11% a release fails it with a probability of 1.9%, and at 0.36% with 14%, although the
   requirement is met. Over 600 intervals, with six allowed, the probability at 0.36% is 0.7%.

The cause is still not named beyond "outside what the guest's counters see": the host's
scheduling of the virtual CPUs is the remaining candidate, and the guest cannot measure it below
the steal time it reports. The decision this evidence supports is the one the roadmap's risk table
foresaw for that case: judge SRS-PERF-022 on a soak long enough to measure a rate of 1%, and close
the report with the evidence that the peaks are rare and lose nothing.
