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
soak (each pipeline thread on a CPU of its own) follows, to test the next candidate, the
threads' movement between CPUs.
