# Review of release 2.0.0: measurements

`soak/`: `tools/soak.py build/release/minidaq/apps OUT --minutes 30` on 2026-11-16, 17:00 to
17:31 UTC, on the branch of the review (the `release` preset; the product code is that of 2.0.0
but for MDQ-PR-078, which `minidaq_server` does not use), on a 4-CPU virtual machine like the
reference machine. It is the first run with the finer measure of MDQ-PR-064: each sample also
holds the largest one-second steal time and the largest one-second run-queue wait of one server
thread (`/proc/PID/task/*/schedstat`), with that thread's name.

What it shows: no interval had a 99th percentile above 10 ms (at most 8.52 ms), so the run saw no
peak of the kind MDQ-PR-064 reports and cannot name its cause yet. The per-second measure works
and is not small: a thread waited on a run queue for a median of 31 ms per second (mostly
`mdq-sort`, then `mdq-write` and `mdq-decode`), and up to 204 ms in one second during the first
150 s, while the interval's 99th percentile stayed at 3 ms. The correlation of the largest wait
with the interval's 99th percentile is 0.13 over 180 intervals. So run-queue waits of this size
alone do not raise the latency above the limit; a peak's cause needs a run that has one, with
this measure beside it. The one-second steal reached 3.07% at most.
