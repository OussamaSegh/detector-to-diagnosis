# Exercise 19.3: notes on the solution

A trend counts only when `b - 2 se > limit`. With 121 samples between 10 and 30 minutes, half a MiB
of noise per sample gives a standard error of about 0.47 MiB/h on the slope. Without the margin, a
flat run with that noise would exceed the 1 MiB/h limit by chance in about one run in 60; with it,
the slope must exceed about 1.9 MiB/h, which noise alone reaches in about two runs in a hundred
thousand. The warm-up keeps the first ten minutes out because memory and latency settle there:
pools fill, pages are touched for the first time, caches warm.

Counters that only count up are checked sample to sample: a decrease means the counter wrapped or
was reset, and either makes every difference computed from it wrong. The stall check compares each
interval's rate with the median interval's, not with the configured rate, so it needs no
configuration and is not fooled by a source that is slower than configured from the start (that is
a different problem, for the throughput requirements).

A single 2 MiB allocation 15 minutes into a 30-minute run looks like a leak to a straight line:
over the 20 minutes after the warm-up, the fitted slope is about 6.7 MiB/h with a standard error of
0.55, and the analysis reports `memory`. That is the wrong verdict for the product and the right
one for a test: the analysis cannot tell a step from a ramp with one line, and a reviewer should
look. Three things tell them apart. Fit the two halves of the window separately: a leak grows in
both, a step in neither. Run longer: a step's slope falls as `1 / T`, a leak's does not. Or read
the allocation counters of the process (the pool statistics of Chapter 2) instead of the resident
memory, which also moves when the kernel reclaims or the allocator returns pages.
