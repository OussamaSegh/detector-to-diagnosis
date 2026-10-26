# Exercise 4.1 notes

**Parsing.** The parser is a small state machine: before `# Histogram` everything is banner
text; inside it, every non-comment line is a row; after it, the `#` summary lines carry one
value per thread. The consistency checks are the point of the exercise: a parser that
silently accepts a truncated file (a run killed with Ctrl-C, a disk that filled up) will
produce believable but wrong percentiles.

**Overflows.** In rt-tests 2.5 the `# Total:` line counts only the samples inside the
histogram range; the overflows are reported separately (we checked this by summing the rows
of the fixture: 14,965 in range plus 9 overflows in a 3-second run at 200 us). A percentile
computed over `Total` alone ignores exactly the samples you care most about. With `-h 20000`
(20 ms), as in the script, overflows should be zero on any sane machine; if they are not, that
is a finding in itself.

**Why nullopt.** When the rank falls among the overflows the honest answer is "more than the
histogram range". Returning the top bin would under-report the tail, which is the one error a
latency report must never make.

**Timer slack.** Under `SCHED_OTHER` an idle machine shows a median near 60 us because the
kernel may delay the timer wake-up of a normal thread by up to its timer slack (50 us by
default) to batch wake-ups; real-time threads get zero slack. This is a power-saving feature,
not a fault. Section 4.4 shows the same effect with `minidaq_jitter --slack-ns 1`.

**Reference results** (book machine: 4 vCPU Xeon at 2.30 GHz in a Firecracker VM, kernel 6.18
PREEMPT_DYNAMIC, 30 s at 200 us on CPU 1, about 150,000 samples idle; microseconds):

| Run        | p50 | p99 | p99.9 | p99.99 | max   |
|------------|-----|-----|-------|--------|-------|
| idle_other | 60  | 80  | 171   | 815    | 2202  |
| idle_fifo  | 10  | 26  | 96    | 978    | 6655  |
| load_other | 66  | 103 | 6604  | 10441  | 12603 |
| load_fifo  | 17  | 41  | 267   | 1457   | 8431  |

The VM's maxima are dominated by the hypervisor; expect lower maxima on bare metal (verify on
your scanner's acquisition PC).
