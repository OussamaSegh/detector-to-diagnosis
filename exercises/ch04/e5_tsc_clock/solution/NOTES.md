# Exercise 4.5 notes

**Calibration error.** Each pair of reads is bracketed by two TSC reads; the bracket width
bounds the error of that pair (tens of nanoseconds, unless the thread was preempted in
between). Over a 50 ms calibration, a 100 ns error is 2 ppm. The 0.1% tolerance in the test
leaves room for a VM, where the hypervisor can deschedule the vCPU between reads.

**Why not just use the TSC everywhere.** The kernel already uses it: with the `tsc` clock
source, `clock_gettime(CLOCK_MONOTONIC)` reads the TSC in the vDSO (no system call) and
applies the kernel's NTP-adjusted conversion. The 28 ns on the book's VM is that conversion
plus the vDSO's sequence-lock retry loop; on bare metal it is typically about 20 ns (verify on
the acquisition PC). A private TSC clock saves a few nanoseconds per read but does not follow
NTP or PTP adjustments, drifts from `CLOCK_MONOTONIC` over hours, and is only valid if the TSC
is invariant and synchronized across sockets. Use it for short intervals on one machine
(benchmarks, per-stage timing), never for event timestamps.

**Detector timestamps.** The coincidence window is a few nanoseconds; no PC clock read
through an operating system is that precise or that stable. NeuroLF's timestamps come from
the front-end electronics' common clock (assumption: confirm with team); the PC only needs
wall-clock time for logs and file metadata (PTP or NTP, Section 4.4).
