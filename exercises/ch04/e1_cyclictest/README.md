# Exercise 4.1 (E): Measure your machine with cyclictest

**Goal.** Measure the wake-up latency of a machine with `cyclictest` from rt-tests, under the
normal scheduler and under `SCHED_FIFO`, idle and loaded, and turn its raw histogram output
into the percentiles the chapter uses. You will write the parser that every later measurement
script in this book reuses.

**Time.** 60 minutes (plus about 3 minutes of measurement per run).

**Tasks.**
1. Implement `ex::parse_cyclictest(std::istream&)` in `cyclictest_report.cpp`. It reads the
   output of `cyclictest -h <N> -q` for one or more threads:
   - rows `NNNNNN CCCCCC [CCCCCC ...]` after `# Histogram`: latency in microseconds, then one
     count per thread; rows must start at 0 and be consecutive;
   - `# Total:`, `# Min Latencies:`, `# Avg Latencies:`, `# Max Latencies:` and
     `# Histogram Overflows:`, one value per thread;
   - any other line (for example `defaulting realtime priority to 2` or
     `# /dev/cpu_dma_latency set to 0us`) is ignored.
   Throw `std::runtime_error` naming the line number if the input is inconsistent: no
   histogram, a gap in the rows, a column count that changes, or a `Total` that does not
   equal the sum of the rows.
2. Implement `ex::percentile_us(thread, percent)`. The rank must count the overflows too
   (samples above the histogram range), because they are real samples. Return
   `std::nullopt` when the rank lands among the overflows: you only know the value is larger
   than the histogram, and reporting the top bin would under-report.
3. Run `./run_cyclictest.sh` (as root, about 4 x 30 s) and fill in `RESULTS.md`.

**Acceptance tests** (`tests/test_cyclictest.cpp`): the parser on a real two-thread output
captured on the book's machine (`tests/fixtures/`), percentiles with overflows, and rejection
of malformed input.

**Watch out.** `cyclictest -p0` does *not* give you the normal scheduler: when the priority is 0
cyclictest prints `defaulting realtime priority to 2` and runs the measuring thread at
`SCHED_FIFO` priority 2. Use `--policy=other` with no `-p`, and check with `chrt -p <tid>`
while it runs. The script does this.

**Think about it** (answer in your notes): why does the median under `SCHED_OTHER` sit near
60 us on an idle machine when `SCHED_FIFO` gives about 10 us? (Hint: Section 4.4, timer slack.)
