# Real-time Linux: scheduling, isolation and latency {#ch04}

::: box-why
A PET scanner does not wait for software. The front-end electronics send data at the rate
the patient's activity dictates, and the buffers on the boards and in the network card hold
milliseconds of it, not seconds. If the acquisition PC stops reading for longer than that,
data is lost, and with it counts that quantitative imaging depends on. "Fast on average" is
therefore not the requirement. The requirement is "never too slow for too long", which is a
statement about the *tail* of the latency distribution: the 99.9th percentile and the maximum.
A DAQ needs low-latency streaming in C++. On Linux, the code is only half of
that. The other half is how the operating system schedules your threads, where it puts them,
how it handles their memory and how you measure the result. This chapter is about that half.
:::

**A day in the life.** It is your second month. A clinical site reports that one
acquisition in a few hundred ends with a "receiver overflow" warning, always during the
first minute. The acquisition PC has been sized with plenty of headroom: the pipeline runs at
under 30% of its benchmarked throughput. You add the latency histograms from this chapter
and see that the median batch latency is 0.7 ms, as expected, but the maximum during the
first minute is 40 ms. The culprit is not your code. At start-up, the reconstruction service
on the same PC loads its system matrix, the kernel reclaims page cache to make room, and the
first touches of the acquisition's freshly allocated buffers each take a page fault that
waits on reclaim. Locking and prefaulting the buffers at start-up, and pinning the hot
threads away from the reconstruction service, removes the overflows. The fix took an hour.
Knowing where to look took this chapter.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Explain how Linux decides which thread runs (the normal scheduler, `SCHED_FIFO` and
   `SCHED_RR`), what a `PREEMPT_RT` kernel changes, and why real-time throttling exists.
2. Pin threads to CPUs, isolate CPUs from the operating system and interrupts, and design a
   CPU layout for a pipeline that never puts two busy real-time threads on one CPU.
3. Keep page faults off the hot path with `mlockall`, prefaulting and huge pages, and measure
   what a page fault costs.
4. Choose the right clock for each job, explain the time-stamp counter (TSC), timer slack and
   precise periodic sleeping, and say why a PET DAQ timestamps events in hardware.
5. Measure latency honestly: percentile histograms with fixed memory, cyclictest, and
   end-to-end latency free of coordinated omission.

## Prerequisites and estimated time {.unnumbered}

Chapters 2 and 3: caches and allocation, the five-stage pipeline and its channels, and
`std::latch`. You need a Linux machine on which you can run as root (or with `CAP_SYS_NICE` and
`CAP_IPC_LOCK`), with `rt-tests` and `stress-ng` installed; a virtual machine works for
everything except bare-metal numbers. Reading: about 3 hours. Exercises: 9 to 12 hours.
Milestone: 3 hours. In the 10-week schedule at the front of the book, this chapter is in week 3,
with Chapter 5 and the first half of Chapter 10.

All measurements in this chapter come from the book's machine: a 4-vCPU Intel Xeon at 2.30 GHz
in a Firecracker virtual machine (VM), Linux 6.18 with `PREEMPT_DYNAMIC` (not `PREEMPT_RT`),
clock source `tsc`, GCC 13.3 at `-O2`, running as root. A hypervisor adds its own pauses, so
every maximum in this chapter is an upper bound for what you would see on bare metal, and
every number needs repeating on the NeuroLF acquisition PC (verify on the acquisition PC).

## Scheduling: who runs, and when

### The intuition

A CPU runs one thread at a time. The scheduler decides which one, every time a thread blocks,
wakes up, or uses up its share. For a server, the goal is fairness and throughput: everyone
makes progress, and the machine is busy. For a DAQ stage, the goal is different. When data
arrives, *this* thread must run *now*, and nothing else should be able to delay it by more
than a known, small amount. Linux offers both kinds of scheduling side by side. Normal threads
share the CPU fairly. Real-time threads run whenever they are runnable and preempt every
normal thread.

### The normal scheduler

Threads under the default policy, `SCHED_OTHER` (also called `SCHED_NORMAL`), share each CPU
in proportion to their weight, which comes from their nice value. Since Linux 6.6 the
algorithm that picks the next thread is EEVDF (earliest eligible virtual deadline first),
which replaced the selection logic of the older CFS (completely fair scheduler). The details
differ, but the property that matters here is the same: a normal thread that wants to run gets
a *share* of the CPU, and how long it waits before it runs depends on how many other threads
want that CPU. On an idle machine, that wait is short. Under load, it is a few milliseconds and
sometimes much more. Neither CFS nor EEVDF makes a promise about the worst case.

### Real-time policies: SCHED_FIFO and SCHED_RR

The [real-time policies]{.idx key="SCHED_FIFO"} have static priorities from 1 to 99. The
rules are simple, and that is the point:

- A runnable real-time thread always runs before any normal thread.
- Among real-time threads, the highest priority runs. A higher-priority thread that wakes up
  preempts a lower-priority one immediately.
- Under `SCHED_FIFO`, a thread runs until it blocks, yields or is preempted by a higher
  priority. Under `SCHED_RR`, threads of *equal* priority also take turns in time slices.

There is also `SCHED_DEADLINE`, which schedules threads by runtime, deadline and period
budgets (earliest deadline first with admission control). It is the right tool for periodic
work with known budgets, and the wrong one for a stage that must react to data whenever it
arrives; this book uses `SCHED_FIFO`.

Setting the policy is one call per thread. MiniDAQ wraps it so that a failure is a value, not
an exception, because on a developer laptop or in CI it is expected to fail:

```{.cpp include="minidaq/src/rt/realtime.cpp" snippet="sched"}
```

The call needs the `CAP_SYS_NICE` capability (root has it), or an `RLIMIT_RTPRIO` limit that
allows the priority; on a product you grant the capability to the acquisition service rather
than running it as root (Chapter 7).

### What a real-time priority does, measured

`minidaq_jitter` is the smallest possible real-time program: a loop that sleeps until an
absolute deadline every 200 µs and records how late it woke up. Here it is, pinned to CPU 1
with memory locked, for 15 seconds (about 75,000 wake-ups), idle and then with
`stress-ng --cpu 4 --vm 2 --vm-bytes 256M --io 1` loading every CPU, in microseconds:

| Load | Policy | p50 | p99 | p99.9 | p99.99 | max |
|---|---|---|---|---|---|---|
| idle | `SCHED_OTHER` | 60.4 | 108.5 | 1,040 | 2,007 | 2,465 |
| idle | `SCHED_FIFO` 80 | 10.4 | 29.3 | 774 | 8,389 | 9,623 |
| load | `SCHED_OTHER` | 67 | 7,668 | 13,238 | 24,642 | 25,790 |
| load | `SCHED_FIFO` 80 | 17 | 51.5 | 2,720 | 12,255 | 13,411 |

Two effects are visible. Under load, the normal policy's p99 is 7.7 ms, because the jitter
loop now competes with four CPU hogs for its share; with `SCHED_FIFO` the p99 stays at 52 µs,
a factor of 150. And even idle, the normal policy's *median* is 60 µs against 10 µs for
`SCHED_FIFO`. That second effect is not scheduling at all; it is timer slack, and Section 4.4
explains it. The idle `SCHED_FIFO` p99.99 of 8 ms is the VM: the hypervisor occasionally
deschedules the whole virtual CPU, and no setting inside the guest can prevent that.

### Starvation, and the throttle that prevents it

The rules that make `SCHED_FIFO` predictable also make it dangerous. A real-time thread that
never blocks starves every lower-priority thread on its CPU, forever. Two failures from
building this chapter's profiles show what that means in practice.

**Two pollers on one CPU.** The first profile gave each of the four busiest stages
`SCHED_FIFO` and, with only three CPUs to spare, put the pair stage (`SCHED_FIFO` 60) on the
same CPU as the source (`SCHED_FIFO` 80). The source polls its input with a short spin before
it yields or sleeps (the `Backoff` of Chapter 3), and at 10 M words/s it is busy almost all the
time. Pair, at lower priority on the same CPU, ran only when the source happened to sleep. Its
service time reached 192 ms and the source dropped 53% of the input. The rule that came out of
it is now a test in Exercise 4.2: **never put two busy `SCHED_FIFO` threads on one CPU**. Give
each one its own CPU, and leave everything else under the normal scheduler.

**The real-time throttle.** Linux protects itself against runaway real-time threads with
[real-time throttling]{.idx key="RT throttling"}: by default, real-time threads may use at most
`sched_rt_runtime_us` = 950,000 µs out of every `sched_rt_period_us` = 1,000,000 µs, leaving
5% for normal threads (both are in `/proc/sys/kernel/`). A `SCHED_FIFO` source stage that is
busy more than 95% of the time is stopped for up to 50 ms each second. The kernel log says so
once: `sched: RT throttling activated`. In the measurements of Section 4.5, this shows up as a
p99 of 44 ms in a run that is otherwise sub-millisecond. Recent kernels implement the reserve
with a "deadline server" for normal threads instead of throttling all real-time threads, but
the default budget is still about 50 ms per second (verify: `Documentation/scheduler/` for
your kernel version). Turning the throttle off (`sched_rt_runtime_us = -1`) is possible and is
done on dedicated real-time systems, but only together with isolated CPUs, so that the
starved "normal threads" are only ones you chose to starve. On a shared CPU it turns a latency
problem into a hung machine.

### PREEMPT_RT

A real-time priority decides who runs *next*. It does not help if the kernel itself cannot be
interrupted: an interrupt handler, a long-running section with preemption disabled, or a
spinlock held by another kernel path all delay your wake-up. The
[`PREEMPT_RT`]{.idx key="PREEMPT_RT"} patch set, merged into the mainline kernel in Linux 6.12,
makes almost all of the kernel preemptible: interrupt handlers run in threads with their own
priorities, and most spinlocks become sleeping locks with priority inheritance. The effect is
on the worst case, not the average: typical worst-case wake-up latencies on suitable hardware
drop from milliseconds to tens of microseconds (verify on the acquisition PC with cyclictest,
Exercise 4.1). The price is a little throughput and more care with interrupt thread priorities.

The book's VM runs a `PREEMPT_DYNAMIC` kernel, which can switch between preemption models at
boot but is not `PREEMPT_RT`; `uname -v` prints `PREEMPT_RT` on a real-time kernel. Whether
NeuroLF's acquisition PC needs `PREEMPT_RT` is a measurement question, not a belief: with
isolated CPUs, a stock kernel may already meet the budget that the front-end buffers allow
(assumption: confirm with team what kernel and budget the product uses).

::: box-mistakes
- **"Real-time means fast."** It means bounded. `SCHED_FIFO` does not make your code faster;
  it removes other threads from in front of it.
- **`cyclictest -p0` as the normal-scheduler baseline.** With priority 0, cyclictest prints
  `defaulting realtime priority to 2` and measures at `SCHED_FIFO` 2. Use `--policy=other`
  without `-p`, and check with `chrt -p <tid>` while it runs. This book's first "normal"
  measurements were in fact real-time ones until that check.
- **Two busy real-time threads on one CPU.** The lower one starves. One busy `SCHED_FIFO`
  thread per CPU.
- **A real-time thread that spins forever on a shared CPU.** It triggers the throttle, or, with
  the throttle off, starves kernel threads that the system needs.
- **Running as root to get the priority.** Grant `CAP_SYS_NICE` and `CAP_IPC_LOCK` to the
  service instead, and keep everything else unprivileged.
:::

## Isolation: giving the hot path its own CPUs

### The intuition

A real-time priority keeps other *threads* out of the way. It does not keep out interrupts,
kernel housekeeping that runs on every CPU (timer ticks, read-copy-update callbacks, per-CPU
workers), or the cache and memory traffic of whatever runs on the neighboring core. The
strongest guarantee you can buy on a general-purpose OS is a CPU that runs nothing but your
stage. Isolation is the set of settings that gets you as close to that as possible.

### Pinning threads

Pinning restricts a thread to a set of CPUs with its *affinity mask*. A pinned thread never
migrates, so it keeps its caches warm and never lands on a CPU you reserved for something
else:

```{.cpp include="minidaq/src/rt/realtime.cpp" snippet="pin"}
```

Note the error handling: the `pthread_*` functions return the error number rather than setting
`errno`, a classic source of wrong error messages. The pipeline applies each stage's settings
from inside the stage's own thread, as its first action, and records what actually happened:

```{.cpp include="minidaq/src/pipeline/acquisition_pipeline.cpp" snippet="enter"}
```

The `std::latch` from Chapter 3 makes `start()` wait until all five stages have applied their
settings. When `start()` returns, `rt_status()` says for every stage whether it is pinned,
which CPU it is running on and whether the policy was applied. That matters: a profile that
silently failed to apply looks exactly like one that worked, until the first overflow.

### A profile is configuration, not code

Which CPU each stage gets depends on the machine, so MiniDAQ reads it from a profile file
(`minidaq/profiles/`). Here is the one used for the measurements in Section 4.5:

```{.text include="minidaq/profiles/rt-fifo.conf"}
```

The layout follows the rule from the previous section. The three busy stages (source, decode
and sort) each get a CPU of their own and `SCHED_FIFO`. Pair and write do little work per
batch and block on their input, so they share CPU 0 with the operating system, under the
normal scheduler. The figure below shows the result, and Exercise 4.2 generates such a
profile from the list of CPUs a process may use.

```{.dot caption="CPU layout of the rt-fifo profile on a 4-CPU machine. Each busy stage runs alone, under SCHED_FIFO, on its own CPU. CPU 0 is the housekeeping CPU: the operating system, interrupts, and the two light stages under the normal scheduler. On the acquisition PC, CPUs 1 to 3 would also be isolated from the scheduler, the timer tick and interrupts." width="75%"}
digraph cpus {
  rankdir=TB; nodesep=0.3; ranksep=0.45; newrank=true;
  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, fillcolor="#eef3fb", color="#4a6fa5", width=1.4];
  edge [fontname="Helvetica", fontsize=9, color="#4a6fa5"];
  subgraph cluster_1 { label="CPU 1"; fontname="Helvetica"; fontsize=10; style="rounded"; color="#c0504d";
    source [label="source\nSCHED_FIFO 80", fillcolor="#fbeeee", color="#c0504d"]; }
  subgraph cluster_2 { label="CPU 2"; fontname="Helvetica"; fontsize=10; style="rounded"; color="#c0504d";
    decode [label="decode\nSCHED_FIFO 70", fillcolor="#fbeeee", color="#c0504d"]; }
  subgraph cluster_3 { label="CPU 3"; fontname="Helvetica"; fontsize=10; style="rounded"; color="#c0504d";
    sort [label="sort\nSCHED_FIFO 70", fillcolor="#fbeeee", color="#c0504d"]; }
  subgraph cluster_hk {
    label="CPU 0: housekeeping"; labelloc=b; fontname="Helvetica"; fontsize=10; style="rounded,filled"; fillcolor="#f7f7f7"; color="#999999";
    os [label="kernel, IRQs,\nother services", fillcolor="#ffffff", color="#777777"];
    pair [label="pair\nSCHED_OTHER"];
    write [label="write\nSCHED_OTHER"];
  }
  { rank=same; source; decode; sort; }
  { rank=same; os; pair; write; }
  source -> decode -> sort;
  sort -> write [style=invis];
  sort -> pair [constraint=false];
  pair -> write;
}
```

### Isolating CPUs from the kernel

Pinning keeps your threads in place, but the scheduler can still put *other* threads on those
CPUs, and the kernel still runs its own work there. On the acquisition PC you go further, with
kernel boot parameters and run-time settings (verify each against the kernel-parameters
documentation of the kernel version you deploy):

- **`isolcpus=1-3`** removes CPUs 1 to 3 from the scheduler's load balancing: no thread lands
  there unless its affinity says so. The kernel documentation now steers new setups toward
  cpusets (the cgroup v2 `cpuset.cpus.partition = isolated` setting), which does the same at run
  time; either way, the result is CPUs that run only what you pin to them.
- **`nohz_full=1-3`** stops the periodic timer tick on those CPUs while a single task runs,
  removing a small interruption every few milliseconds. It needs `rcu_nocbs=1-3` (often
  implied) so that read-copy-update callbacks run elsewhere.
- **Interrupt affinity.** Every interrupt has an affinity mask in
  `/proc/irq/<n>/smp_affinity_list`. Move device interrupts to the housekeeping CPU, and stop
  `irqbalance` from moving them back (or configure it to avoid the isolated CPUs). The
  network card's receive interrupts are the exception: they belong close to the thread that
  reads the data, a topic for the network receiver in Chapter 9.
- **Kernel threads and workqueues.** Unbound workqueues have their own CPU mask in
  `/sys/devices/virtual/workqueue/cpumask`; set it to the housekeeping CPUs.

Two hardware topics complete the picture. **Simultaneous multithreading** (SMT, Intel's
"Hyper-Threading") presents each physical core as two CPUs that share execution units and caches. A
busy stage on one sibling slows the other, so either disable SMT or leave the sibling of each
isolated CPU idle; `lscpu -e` shows which CPUs share a core. **NUMA** (non-uniform memory access):
on a machine with two sockets, memory and PCIe devices are attached to one socket, and access from
the other socket crosses an interconnect. Put the receiving stages on the socket that owns the
network card, and allocate their buffers there (`numactl`, or `mbind`), so that data never crosses
sockets on the hot path. Whether the NeuroLF acquisition PC has one socket or two is something to
find out in your first weeks (assumption: confirm with team).

::: box-mistakes
- **Pinning without checking.** A CPU number that does not exist, or an affinity that a
  container's cpuset forbids, fails quietly unless you check the result. Read `rt_status()`
  (or `/proc/<pid>/task/*/status`) after start-up.
- **Isolated CPUs with interrupts still on them.** `isolcpus` does not move interrupts. Check
  `/proc/interrupts` per CPU during an acquisition.
- **Pinning a busy stage to CPU 0.** CPU 0 handles more interrupts and housekeeping than any
  other on most systems. Keep it for the operating system.
- **Two siblings of one core for two busy stages.** They look like two CPUs and behave like one
  shared core.
:::

## Memory: keeping page faults off the hot path

### The intuition

The addresses your program uses are virtual. The kernel maps them to physical memory one page
(4 KiB on x86-64) at a time, and lazily: `malloc` or `mmap` of 32 MiB only reserves addresses,
and the first write to each page traps into the kernel, which finds a free physical page, zeroes
it and installs the mapping. That trap is a [page fault]{.idx}. A *minor* fault is resolved
from memory; a *major* fault has to read from disk (a page of a memory-mapped file, or one that
was swapped out) and takes milliseconds. Either kind stops your thread at a moment you did not
choose. Chapter 2 removed allocation from the hot path; this section removes the faults that
allocation leaves behind.

### What a page fault costs, measured

Writing 32 MiB of freshly mapped memory twice, and timing both passes, separates the cost of
the faults from the cost of the writes (7 runs, GCC 13.3, `-O2`, transparent huge pages
disabled for the region):

| Pages | Faults | First pass | Second pass | Per fault |
|---|---|---|---|---|
| 4 KiB | 8,192 | 11 to 19 ms | 1.3 to 3.1 ms | 1.2 to 2.0 µs (median 1.5) |
| 2 MiB (transparent huge pages) | 16 | about 2 ms | about 1.2 ms | 52 to 83 µs typical, one of 5 ms |

A minor fault costs about 1.5 µs here, most of it zeroing the page. That is a hundred times
the cost of decoding a batch of singles per page touched, and it arrives in bursts: a new
buffer of 4,096 singles (64 KiB) faults 16 times in a row on first use. Huge pages cut the
number of faults by 512, but each one zeroes 2 MiB, so a single huge-page fault on the hot path
is a 50 µs stall. The lesson is not "use huge pages" or "do not". It is: **take every fault at
start-up**.

### Lock everything, then touch it

`mlockall` pins the process's memory in RAM: no page is ever swapped out or reclaimed, and with
`MCL_FUTURE` every later mapping is faulted in and locked as soon as it is created:

```{.cpp include="minidaq/src/rt/realtime.cpp" snippet="mlock"}
```

`AcquisitionPipeline::start()` calls it before it creates the stage threads when the profile
says `lock_memory = true`. Because of `MCL_FUTURE`, the batches allocated by the channels and
each new thread's stack are then resident from the start. One gap remains: a thread's stack is
mapped when the thread starts, but the kernel grows a stack's *use* page by page, and
`MCL_FUTURE` locks a mapping when it is created, not every page your function will ever
reach. Each stage therefore touches the stack it will need before entering its loop:

```{.cpp include="minidaq/src/rt/realtime.cpp" snippet="prefault"}
```

Two details make this code correct. The buffer is `volatile`, so the compiler cannot remove
the stores to memory nobody reads. And the recursive call comes *before* the loop, so it is not
a tail call: with a tail call the compiler could reuse the frame and touch the same 64 KiB over
and over. You can check the effect with `minidaq::rt::thread_page_faults()`, which reads the
calling thread's fault counters from `getrusage(RUSAGE_THREAD)`; the unit tests do exactly
that.

Exercise 4.4 builds the same idea for a large buffer, an arena that touches every page by
*writing* to it when it is created:

```{.cpp include="exercises/ch04/e4_prefault_arena/solution/prefaulted_arena.cpp" snippet="ctor"}
```

Reading would not be enough. A read of an untouched anonymous page maps the kernel's shared
zero page, read-only; the first write afterwards still faults, to make a private copy. In the
exercise's test, writing every byte of a 32 MiB prefaulted arena costs zero minor faults; the
same writes to plain `mmap` memory cost 8,192.

### Huge pages

The other reason to care about pages is the translation lookaside buffer (TLB), the CPU's cache
of address translations (Chapter 2). With 4 KiB pages, a 1 GiB ring buffer needs 262,144
translations, far more than any TLB holds; with 2 MiB pages it needs 512. For the big buffers a
DAQ keeps (the receive rings and the batch pools), huge pages are usually worth it. Linux
offers two mechanisms:

- **Transparent huge pages** (THP). The kernel backs suitably aligned anonymous memory with
  2 MiB pages when it can. The mode in `/sys/kernel/mm/transparent_hugepage/enabled` is
  `always`, `madvise` (only regions marked with `madvise(MADV_HUGEPAGE)`) or `never`. THP is
  convenient, but the kernel's background `khugepaged` thread may later collapse small pages
  into huge ones, and memory compaction to find free 2 MiB blocks can stall an allocation;
  both are latency sources to keep away from the acquisition (verify: the kernel's
  `transhuge` documentation). The book's VM runs THP in `always` mode, which is why Exercise
  4.4's test disables it for its baseline.
- **Explicit huge pages** (hugetlbfs). You reserve a number of huge pages at boot
  (`hugepages=` on the kernel command line) or early at run time (`/proc/sys/vm/nr_hugepages`),
  and map them with `mmap(..., MAP_HUGETLB, ...)` or from a file on a hugetlbfs mount. The
  memory is reserved, never swapped and never collapsed; allocation fails cleanly if the pool
  is empty. For a product, explicit huge pages are the predictable choice: allocate the big
  buffers from them at start-up, prefault them, and fail the start-up loudly if the pool is too
  small.

### The kernel entries that are left

With memory locked and prefaulted, the remaining ways for a stage to enter the kernel are the
ones it calls itself: system calls (a `write` to a log file, a `clock_gettime` that falls out
of the virtual dynamic shared object, or vDSO, into a real system call), and blocking on a
lock. Keep logging off the hot path (in Chapter 6 the stages only count, and a monitor thread in the control service turns counts and faults into log and audit records), never
call a function that may allocate (Chapter 2), and count the faults in tests so that a
regression shows up as a failing test rather than as a field report.

::: box-mistakes
- **`mlockall` and nothing else.** It locks what is mapped. Stack pages your code has not
  reached yet, and memory a library maps lazily, can still fault. Prefault the stack and the
  buffers, and measure.
- **Touching pages by reading.** It maps the zero page; the first write still faults.
- **Huge pages allocated on the hot path.** One fault zeroes 2 MiB: about 50 µs on the book's
  machine. Reserve and touch them at start-up.
- **Forgetting the limit.** `mlockall` without `CAP_IPC_LOCK` fails once the process exceeds
  `RLIMIT_MEMLOCK` (8 MiB by default on many distributions). Check the return value; MiniDAQ
  reports it in `memory_locked()`.
:::

## Time: clocks, the TSC, PTP and timer slack

### The intuition

A DAQ uses time in three different ways, and each needs a different clock. *Event time*, the
picosecond timestamps of singles, comes from the detector electronics; the PC never makes it
up. *Interval time* for latency measurements and timeouts must never jump. *Wall-clock time*
for logs and file metadata must match the rest of the hospital. Mixing them up is a classic
source of bugs that appear twice a year, when daylight saving time changes, or once, when NTP
corrects a clock that drifted.

### Which clock for what

Linux exposes several clocks through `clock_gettime` (see the `clock_gettime(2)` manual page):

| Clock | Use | Jumps? |
|---|---|---|
| `CLOCK_MONOTONIC` | intervals, timeouts, latency; `std::chrono::steady_clock` | never; rate adjusted by NTP |
| `CLOCK_MONOTONIC_RAW` | comparing against hardware counters | never; not rate adjusted |
| `CLOCK_BOOTTIME` | like monotonic, but counts suspend | never |
| `CLOCK_REALTIME` | wall-clock time for logs; `std::chrono::system_clock` | yes, when set or corrected |

MiniDAQ's `monotonic_ns()` is `steady_clock`, which libstdc++ implements with
`CLOCK_MONOTONIC`. With the `tsc` clock source, reading it does not enter the kernel: the vDSO
reads the time-stamp counter and converts it in user space. On the book's VM, one read costs
28.3 ns (`BM_MonotonicClock` in `bm_histogram`); about 20 ns is typical on bare metal (verify on
the acquisition PC). That is cheap, but not free: at 50 M singles per second you do not
timestamp singles with it, you timestamp batches.

### The time-stamp counter

The [TSC]{.idx key="TSC"} is a 64-bit counter in every x86 core, read with the `rdtsc`
instruction in a few nanoseconds. On modern CPUs it is *invariant*: it ticks at a constant rate
regardless of frequency scaling (the `constant_tsc` flag in `/proc/cpuinfo`) and keeps ticking
in deep idle states (`nonstop_tsc`). The book's VM reports both, plus `tsc_known_freq`.
Exercise 4.5 builds a clock that reads the TSC and converts ticks with a factor calibrated
against `CLOCK_MONOTONIC`:

```{.cpp include="exercises/ch04/e5_tsc_clock/solution/tsc_clock.cpp" snippet="calibrate"}
```

The bracketing trick (read the TSC before and after the clock, take the midpoint) bounds the
calibration error by the time between the two reads. The exercise's test checks agreement with
`CLOCK_MONOTONIC` within 0.1% over 100 ms. A private TSC clock is useful for benchmarks and
for timing short intervals on one machine. It is not a wall clock: it does not follow NTP or
PTP corrections, and across sockets it is only valid if the firmware synchronized the counters
(verify on multi-socket machines).

### PTP, NTP and the hardware clock

Why not timestamp singles with the PC's clock? Because a coincidence window is a few
nanoseconds, and the timing resolution of the detector is tens of picoseconds. No clock read
through an operating system, with its tens of nanoseconds of read cost and microseconds of
scheduling jitter, comes close. NeuroLF, like every PET system, timestamps singles in the
front-end electronics from a common clock distributed to all boards (assumption: confirm with
team how the clock is distributed and how time markers relate board time to PC time). The PC's
job is to keep board time and wall-clock time apart, and to relate them when needed (Chapter 9
adds time markers to the stream).

For wall-clock time, the PC synchronizes with the network. NTP (Network Time Protocol)
typically keeps a clock within a millisecond or so on a local network. PTP (Precision Time
Protocol, IEEE 1588) with hardware timestamping in the network card reaches sub-microsecond
accuracy; on Linux, the `linuxptp` project's `ptp4l` synchronizes the card's clock and
`phc2sys` the system clock to it. A DAQ rarely needs PTP for its data, but the hospital's
systems may need it for correlating events across devices.

### Sleeping precisely: absolute deadlines and timer slack

A periodic task should sleep until an *absolute* deadline. Sleeping for a relative interval
accumulates every oversleep into a drift; sleeping until "previous deadline plus period" does
not. This is `minidaq_jitter`'s loop:

```{.cpp include="minidaq/apps/minidaq_jitter.cpp" snippet="loop"}
```

Now the 60 µs median of the first table. Linux lets the kernel delay the expiry of a normal
thread's timer by up to its [timer slack]{.idx key="timer slack"}, so that wake-ups from many
threads can be batched and the CPU sleeps longer; the default is 50 µs
(`/proc/self/timerslack_ns` reads 50000 on the book's machine). Real-time threads get no slack.
You can set it per thread with `prctl(PR_SET_TIMERSLACK, ns)`, which `minidaq_jitter --slack-ns`
does (idle, `SCHED_OTHER`, pinned, microseconds):

| Timer slack | min | p50 | p99 | p99.9 | max |
|---|---|---|---|---|---|
| default (50 µs) | 59.3 | 60.4 | 108.5 | 1,040 | 2,465 |
| 1 ns | 9.4 | 10.4 | 25.7 | 143 | 1,866 |

With 1 ns of slack, a normal thread on an idle machine wakes up as promptly as a real-time one.
Under load it still waits for its share; timer slack is about *when the timer fires*, the
policy is about *who runs once it has*. The remaining 10 µs is the cost of the timer interrupt,
the wake-up and the context switch in this VM.

::: box-mistakes
- **`system_clock` for durations.** It jumps when NTP or an administrator sets the time. Use
  `steady_clock` for everything that is an interval.
- **Relative sleeps in a periodic loop.** `sleep_for(period)` drifts by every oversleep. Use
  an absolute deadline (`clock_nanosleep` with `TIMER_ABSTIME`, or `sleep_until`).
- **Measuring with default timer slack and blaming the scheduler.** A 50 µs floor on every
  wake-up of a normal thread is slack, not scheduling.
- **PC timestamps for events.** Event time comes from the hardware. The PC's clocks are for
  intervals and logs.
:::

## Measuring latency

### The intuition

Latency is a distribution, and the part you care about is the tail. A DAQ that processes 99.9%
of batches in under a millisecond and one in a thousand in 50 ms will overflow its buffers
every few seconds at high rates. The mean of that distribution is about 1 ms and says nothing
about the problem; neither does the median. What answers "will we lose data?" is a high
percentile (p99.9, p99.99) and the maximum, measured over a long run, at the real load, and
reported together with the number of samples and any data that was dropped. This section builds
the tools to do that and then applies them to MiniDAQ.

### A histogram with fixed memory

You cannot store every sample: an hour at 10,000 batches per second is 36 million of them.
And you cannot compute percentiles from a running mean and variance. What works is a
histogram whose buckets have a bounded *relative* width, so that every reported value is
accurate to a known percentage, from nanoseconds to minutes. MiniDAQ's `LatencyHistogram`
follows the scheme of Gil Tene's HdrHistogram (it is not that library): values below 256 get
one bucket each, and every power-of-two range above that is split into 128 equal buckets, so
the relative error is below 1/128 (0.8%):

```{.cpp include="minidaq/include/minidaq/metrics/latency_histogram.hpp" snippet="index"}
```

The whole range up to 2^40^ ns (about 18 minutes) takes 4,353 buckets, 34 KiB, allocated
once. Recording is one bucket update and a few counter updates, with no allocation, no lock and
no system call:

```{.cpp include="minidaq/include/minidaq/metrics/latency_histogram.hpp" snippet="record"}
```

Each histogram has a single writer, the stage that owns it, so a plain relaxed load followed by
a relaxed store is enough; a `fetch_add` would be a locked instruction on x86 for no benefit.
Other threads may read the counts at any time and see a slightly stale but never torn value.
`bm_histogram` measures 2.71 ns per `record()` on the book's machine, and 0.79 µs to compute
one percentile by walking the buckets. Percentiles are reported as the *highest* value of the
bucket they fall in, so the histogram may over-report by up to 0.8% but never under-reports.

The pipeline records two kinds of latency. Each stage records its *service time* per batch,
the time spent processing it, not waiting for it. The write stage records *end-to-end latency*
per batch, from `Batch::origin_ns` to the moment its coincidences are written. Exercise 4.3 adds
interval queries ("p99.9 over the last second"), which Chapter 6 exposes through the control
API.

### Coordinated omission, and the time it was in our own tool

Here is a mistake that almost every latency measurement makes once. A load generator that waits
for each response before it sends the next request "coordinates" with the system under test:
while the system stalls, the generator stops sending, so a 200 ms stall produces one slow
sample instead of the 200 that an independent stream of requests would have seen. Gil Tene
named this [coordinated omission]{.idx key="coordinated omission"}. Exercise 4.6 reproduces it
in a deterministic simulation: 10,000 requests every 1 ms, each served in 100 µs except one that
stalls for 200 ms. The naive measurement reports p99 = p99.99 = 100 µs; measured from when each
request *should* have started, p99 is 110 ms: the requests queued by the stall drain at 100 µs
each while a new one is due every 1 ms, so the k-th of them waits about 200 − 0.9k ms, and the
100th worst of the 10,000 (k = 99) about 110 ms. The standard correction, when you can only work
with the naive samples and know the intended interval, adds the samples the generator omitted:

```{.cpp include="exercises/ch04/e6_coordinated_omission/solution/omission.cpp" snippet="corrected"}
```

A DAQ looks immune: the detector does not wait for the PC. But the measurement is taken by the
PC. In MiniDAQ's first version, the source stage set `origin_ns` when it *read* the first word
of a batch. When the source thread itself was delayed (preempted, throttled, or simply slower
than the input for a moment), the words that piled up meanwhile were read late and stamped late,
and the stall disappeared from the histogram, exactly as in the exercise. The fix is to take the
time at which the data was *due*. A real receiver gets that from the hardware (a timestamp from
the network card, or the board's time marker, Chapter 9); the simulator knows its own schedule,
so `PacedSource::due_ns(index)` returns it, and the pipeline uses it when the configuration
provides one:

```{.cpp include="minidaq/src/pipeline/acquisition_pipeline.cpp" from="// Fill the batch until it is full" to="if (b->full()"}
```

With the fix, the idle `SCHED_FIFO` runs of the next section show a p99 of 44 ms instead of a
p99.99 of 52 ms: the real-time throttle had been stalling the source all along, and the old
measurement hid how often. Under load the difference is far larger, as the next section shows. A test, `Pipeline.MeasuresFromDueTimeWhenTheSourceKnowsIt`, now
checks that the pipeline uses the due time.

### cyclictest: the machine's own floor

Before you blame your code, measure the platform. [cyclictest]{.idx key="cyclictest"}, from
the `rt-tests` package, is the standard tool: it does what `minidaq_jitter` does, with options
for many threads and policies, and prints a histogram. It also writes 0 to
`/dev/cpu_dma_latency` while it runs, which keeps the CPU out of deep idle states whose exit
latency would otherwise add to every wake-up. Its numbers are the floor that no application on
that machine can beat. On the book's machine (30 s at 200 µs on CPU 1, `-m`, about 150,000
samples idle; microseconds):

| Load | Policy | p50 | p99 | p99.9 | p99.99 | max |
|---|---|---|---|---|---|---|
| idle | `--policy=other` | 60 | 80 | 171 | 815 | 2,202 |
| idle | `--policy=fifo -p80` | 10 | 26 | 96 | 978 | 6,655 |
| load | `--policy=other` | 66 | 103 | 6,604 | 10,441 | 12,603 |
| load | `--policy=fifo -p80` | 17 | 41 | 267 | 1,457 | 8,431 |

The pattern matches `minidaq_jitter`: timer slack sets the normal policy's median, and under
load `SCHED_FIFO` keeps p99.9 at a quarter of a millisecond where the normal policy reaches
6.6 ms. The maxima in the milliseconds, under every policy, are the hypervisor; on bare metal
with `PREEMPT_RT` and isolated CPUs, published cyclictest maxima are in the tens of microseconds
(verify on the acquisition PC, Exercise 4.1). Exercise 4.1 also found a detail of cyclictest's
output that matters for every parser: the `# Total:` line counts only samples inside the
histogram range, and the overflows are reported separately. A percentile computed over
`Total` alone ignores the samples you care about most.

### MiniDAQ's end-to-end latency

`minidaq_latency` runs the full pipeline from a `PacedSource` at a fixed rate, with the drop
policy at the entry (the "hardware" does not wait), and prints every stage's service time and
the end-to-end latency. A rate is essential: a source that produces as fast as it can fills
every queue and measures queueing, not processing. These are runs at 10 M words/s for 20 s with
batches of 4,096 words (about 49,000 batches per run when nothing is lost), with the three
profiles of `minidaq/profiles/`, idle and under the same `stress-ng` load as before, three runs
each; the median of the three runs, with the range in brackets:

First, what was delivered. Of the 200 M words offered in each run, "dropped" is the share
the source read and discarded because the pipeline was full; "behind" is the share that was due
but never read at all, because the source itself could not keep up (`minidaq_latency` now prints
it as `behind schedule`):

| Load | Profile | Dropped | Behind at stop |
|---|---|---|---|
| idle | all three | 0 | 0 |
| load | default | 11.6% [10.6, 12.8] | 24% [23, 31] |
| load | rt-pin | 4.9% [4.9, 8.2] | 37% [35, 37] |
| load | rt-fifo | 0 | 0 |

Then the end-to-end latency, measured from when the data was due, in **milliseconds**:

| Load | Profile | p50 | p99 | p99.9 | max |
|---|---|---|---|---|---|
| idle | default | 0.78 | 1.8 [1.6, 2.2] | 5.8 [4.3, 14] | 12.5 [6.4, 19] |
| idle | rt-pin | 0.75 | 2.2 [1.4, 3.2] | 5.8 [5.0, 8.7] | 12.2 [10, 17] |
| idle | rt-fifo | 0.70 | 44 [44, 45] | 50 [49, 50] | 53 [51, 53] |
| load | default | 2,835 | 4,765 | 4,918 | 4,918 |
| load | rt-pin | 3,221 | 7,315 | 7,416 | 7,420 |
| load | rt-fifo | 5.6 [5.0, 5.9] | 52 [50, 215] | 61 [60, 281] | 69 [63, 291] |

Five lessons come out of these tables, and each one changed something in the book.

**Idle, the profiles barely matter, except one that hurts.** Without load, all three profiles
deliver everything with a median of about 0.75 ms, which is mostly the time to fill a 4,096-word
batch at 10 M words/s (0.41 ms) plus the source's own generation cost (the synthetic source
spends about 87 ns per word, so its service time per batch is 356 µs). The rt-fifo profile is the
exception: its p99 is 44 ms. The source thread is busy about 90% of the time and runs at
`SCHED_FIFO`, so it hits the real-time throttle and is stopped for tens of milliseconds every
second, on all three runs. On a machine without isolated CPUs, a busy real-time thread is worse
than none.

**Under load, normal threads cannot keep up.** With `stress-ng` on all four CPUs, the default
profile's source gets only its fair share of a CPU, falls behind, and never catches up: at the
end of a run a quarter of the input has not even been read, and another 12% was read and
dropped. Latency measured from when data was due grows for the whole run, to seconds. On a real
scanner, that is a front-end buffer overflow within milliseconds of the load starting.

**Pinning without priority makes it worse.** The rt-pin profile pins the source to CPU 1, where a
load process also runs. Unpinned, the scheduler could at least move the source to a less busy
CPU; pinned, it cannot. More than a third of the input is never read. Pinning is half of an
isolation strategy, and only the half that helps once the CPU is reserved.

**Real-time priority keeps the pipeline alive under load.** With rt-fifo, nothing is dropped
and nothing falls behind: the busy stages preempt the load. The median rises to 5.6 ms because
the normal-scheduler stages on CPU 0 (pair and write) now share it with the load, and the tail
is set by the throttle (about 50 ms) and, in one run of three, by a 0.2 to 0.3 s stall that the
other two did not see; one bad run in three is the reason for repeating runs. On the acquisition
PC the remaining fixes are the ones from Section 4.2: isolate CPUs for the busy stages, keep
other services off them, and size the stages so that no real-time thread is busy anywhere near
95% of the time.

**The first version of this table was wrong.** It was measured with read-time origins, before
the coordinated-omission fix. It reported, for the loaded default profile, a median of 20 ms and
a maximum of 124 ms: bad, but survivable. The truth was seconds. The same run had already printed
the drop count that should have raised the alarm, and the backlog was not printed at all. That is
why `minidaq_latency` now reports both next to the percentiles, and why a latency number without
its drop and backlog counts is not a result.

### Reading a latency report

Every latency number in this chapter came with the machine, the load, the duration, the number
of samples and the drops. That is the minimum for a latency report to mean anything:

- **The load and the rate.** Latency at 10% load and at 90% load are different quantities.
- **The duration and the number of samples.** A p99.99 from 10,000 samples is a single sample.
  You need at least 100 times more samples than 1 / (1 - percentile) for a stable estimate.
- **Drops.** Dropped data has no latency. A run with drops is a failed run, not a fast one.
- **The tail and the maximum, not the mean.** Report p50, p99, p99.9, p99.99 and the maximum.
- **Repetitions and spread.** One run of a VM is an anecdote. Three runs with a range is a
  measurement.

::: box-mistakes
- **Reporting the mean.** It hides exactly the events that overflow buffers.
- **Measuring from when the data was read.** A delayed reader stamps delayed data late and the
  stall vanishes. Measure from when the data was due (coordinated omission).
- **Percentiles from too few samples, or without the overflows.** Count every sample, and run
  long enough for the percentile you report.
- **Latency without load.** Measure at the rate the product must sustain, and at the worst
  co-located load it will see (reconstruction running, a disk copy, a service tool).
- **A latency number without the machine.** Every published number names its machine, kernel,
  compiler, flags and profile.
:::

::: box-regulated
Real-time behavior is where software requirements meet the hardware they run on.

- **Timing requirements need numbers.** "The acquisition shall not lose data" is not testable.
  "At 10 M singles/s, the end-to-end latency p99.99 shall be below X ms over a 1-hour
  acquisition, with zero drops, on the specified acquisition PC and configuration" is. Such
  requirements belong in the software requirements specification, with X derived from the
  front-end buffer size (Chapter 14 traces them to tests).
- **The configuration is part of the product.** Kernel version and parameters, the real-time
  profile, CPU isolation, BIOS settings (SMT, power states) and the PC model all affect the
  result, so they are configuration items under configuration management, and changing any of
  them requires re-running the timing verification. IEC 62304 treats the operating system as
  SOUP (software of unknown provenance), with its version recorded and its anomalies evaluated
  (Chapter 14).
- **Failing safe at start-up.** MiniDAQ reports a profile that failed to apply instead of
  refusing to run, which is right for development. For a clinical acquisition, decide (and
  record in the risk analysis, Chapter 15) whether an acquisition may start when memory locking
  or real-time scheduling failed, or must refuse with a clear message.
- **Verification evidence.** Keep the raw histograms of the verification runs, not just the
  percentiles. The histogram is the evidence; a table typed from it is a claim.
:::

::: box-askteam
1. Which kernel does the acquisition PC run (version, `PREEMPT_RT` or not), and who owns its
   configuration (boot parameters, isolated CPUs, interrupt affinity)?
2. How much buffering do the front-end boards and the network card provide, in milliseconds at
   peak rate? That is the latency budget the PC must meet.
3. Which threads of the current acquisition software run with real-time priority, on which
   CPUs, and what else runs on the PC during an acquisition (reconstruction, viewers, backups)?
4. How are singles timestamped, how is the clock distributed to the boards, and how is board
   time related to PC time?
5. Is there an existing latency or overflow test, how long does it run, and where are its
   results kept?
:::

## Exercises {.unnumbered}

**Exercise 4.1 (E): Measure your machine with cyclictest.** *Goal:* measure wake-up latency
under the normal scheduler and `SCHED_FIFO`, idle and loaded, and write the parser that turns
cyclictest's histogram into percentiles. *Starter:* `exercises/ch04/e1_cyclictest/` (with
`run_cyclictest.sh` and a `RESULTS.md` template). *Acceptance:* `tests/test_cyclictest.cpp`
passes: the real two-thread fixture parses with the right totals, minima, maxima and overflows;
percentiles count the overflows and return "no value" when the rank falls among them; malformed
input is rejected with the line number. `RESULTS.md` holds your four runs with the policies
confirmed by `chrt -p`. *Time:* 60 minutes plus measurement.

**Exercise 4.2 (M): Pin the pipeline stages and compare the tail.** *Goal:* parse Linux CPU
lists, place the five stages on the CPUs you may use, generate a real-time profile, and measure
the end-to-end p99.9 with and without pinning and `SCHED_FIFO`, idle and loaded. *Starter:*
`exercises/ch04/e2_pin_stages/`. *Acceptance:* `tests/test_pin_stages.cpp` passes (CPU-list
parsing and its error cases, placement for 1 to 8 CPUs, never two FIFO stages on one CPU, a
round trip through the library's profile format), and your notes hold the six measurements
with drops. *Time:* 2 hours.

**Exercise 4.3 (H): Per-stage latency you can query while it runs.** *Goal:* one histogram per
stage, snapshots from any thread, percentiles over the interval between two snapshots without
resetting anything, and exact JSON for the control API. *Starter:*
`exercises/ch04/e3_stage_histograms/`. *Acceptance:* `tests/test_stage_histograms.cpp` passes
in all four presets, including the test in which a writer records while a reader takes
snapshots and every sample must land in exactly one interval. *Time:* 3 hours.

**Exercise 4.4 (M, extra): An arena that never page-faults on the hot path.** *Goal:* a bump
arena whose pages are faulted in, and optionally locked, when it is created. *Starter:*
`exercises/ch04/e4_prefault_arena/`. *Acceptance:* `tests/test_arena.cpp` passes: allocation
rules, move semantics, and fewer than 64 minor faults to write all of a 32 MiB arena where plain
`mmap` memory takes thousands (the fault test is skipped in sanitizer builds). *Time:* 90
minutes.

**Exercise 4.5 (E, extra): A calibrated TSC clock.** *Goal:* read the TSC, detect an invariant
TSC from `/proc/cpuinfo`, and calibrate ticks against `CLOCK_MONOTONIC`. *Starter:*
`exercises/ch04/e5_tsc_clock/`. *Acceptance:* `tests/test_tsc.cpp` passes: whole-word flag
matching, a plausible rate, and agreement with `CLOCK_MONOTONIC` within 0.1% over 100 ms.
*Time:* 60 minutes.

**Exercise 4.6 (M, extra): Coordinated omission.** *Goal:* simulate a closed-loop load
generator with one stall, and show that the naive measurement hides it while measuring from the
intended start and the HdrHistogram-style correction both expose it. *Starter:*
`exercises/ch04/e6_coordinated_omission/`. *Acceptance:* `tests/test_omission.cpp` passes:
naive p99 at 100 µs, both corrected p99s above 90 ms and within 15% of each other, and exact
sample counts. *Time:* 90 minutes.

## MiniDAQ milestone: deterministic acquisition on Linux {.unnumbered}

::: box-milestone
**Goal.** The pipeline applies a real-time profile (memory locking, stack prefaulting,
per-stage CPU and scheduling policy) before it starts, reports what was applied, records
per-stage service time and end-to-end latency in fixed-memory histograms measured from when
data was due, and comes with two tools that measure the platform and the pipeline.
**Start:** tag `ch03`. **End:** tag `ch04`.
:::

1. Add `minidaq/include/minidaq/core/clock.hpp` (`monotonic_ns()`) and
   `minidaq/include/minidaq/metrics/latency_histogram.hpp`.
2. Add the real-time helpers `minidaq/include/minidaq/rt/realtime.hpp` and
   `minidaq/src/rt/realtime.cpp`: pinning, scheduling, thread names, timer slack, stack
   prefaulting, `mlockall`, per-thread page-fault counters, and the profile parser and
   formatter.
3. Extend the pipeline: `PipelineConfig::rt`, `max_batch_delay` (a partially filled batch is sent
   once its oldest word is 500 µs old, so that low rates do not wait for full batches) and
   `due_time_ns`; `enter_stage()` in every stage with a `std::latch` so that `start()` returns
   after all settings are applied; `stage_latency()`, `end_to_end_latency()`, `rt_status()` and
   `memory_locked()`.
4. Add `minidaq/include/minidaq/sim/paced_source.hpp` and the profiles `default.conf`,
   `rt-pin.conf` and `rt-fifo.conf` under `minidaq/profiles/`.
5. Add the tools `minidaq/apps/minidaq_jitter.cpp` and `minidaq/apps/minidaq_latency.cpp`, and
   `benchmarks/bm_histogram.cpp`.
6. Add the unit tests `test_latency_histogram.cpp`, `test_realtime.cpp` and
   `test_paced_source.cpp`, and extend `test_pipeline.cpp` with the latency, profile and due-time
   tests. Tests must pass without privileges: a test that needs `CAP_SYS_NICE` or
   `CAP_IPC_LOCK` checks for it and skips with a message.
7. Run `minidaq_latency` on your machine with the three profiles, idle and loaded, three times
   each, and record the results with the machine description in your learning log.

**Definition of done.** `ci/run_all.sh` is green on all four presets. `start()` returns with a
complete `rt_status()`. `minidaq_latency --rate 10e6 --seconds 20 --profile
minidaq/profiles/rt-pin.conf` reports zero drops on an idle machine, and the latency table
includes p99.9, p99.99 and the maximum. Tag `ch04`.

## Check yourself {.unnumbered}

1. Why is the mean latency nearly useless for a DAQ?
2. What does a page fault cost, and how do you prevent it on the hot path?
3. Under the normal scheduler, an idle machine wakes a sleeping thread about 60 µs late; under
   `SCHED_FIFO`, about 10 µs. What causes the difference, and how do you remove it without a
   real-time policy?
4. Why must two busy `SCHED_FIFO` threads never share a CPU? What happened when this chapter's
   first profile did it?
5. A `SCHED_FIFO` stage on a non-isolated CPU shows a latency spike of about 50 ms roughly once a
   second. What is the most likely cause, how do you confirm it, and what are the fixes?
6. What does `PREEMPT_RT` change, and why does it affect the worst case much more than the
   average?
7. Name three sources of interruption that pinning a thread does not remove, and the setting
   that addresses each.
8. Why does `mlockall(MCL_CURRENT | MCL_FUTURE)` alone not guarantee a fault-free stage, and
   why does touching a fresh page by reading it not help?
9. Which clock do you use for a timeout, for a log timestamp, and for the time of a single? Why
   not the same one for all three?
10. What is coordinated omission? Explain how it could hide a stall in a DAQ even though the
    detector never waits for the PC.
11. You have 50,000 latency samples. Which of p99, p99.9 and p99.99 can you report with
    confidence, and why?
12. cyclictest reports `# Total: 14965` and `# Histogram Overflows: 9`. Over how many samples
    do you compute the p99.9, and what do you report if its rank falls among the overflows?

## Summary {.unnumbered}

- A DAQ's requirement is a bounded tail: report p99.9, p99.99 and the maximum, with the load,
  the duration, the sample count and the drops. The mean is nearly useless.
- `SCHED_FIFO` makes a runnable thread run before every normal thread. Under load it kept the
  wake-up p99 at 52 µs where the normal policy reached 7.7 ms on the book's machine.
- One busy real-time thread per CPU. Two on one CPU starve the lower one (192 ms here), and a
  real-time thread busy more than 95% of a second is throttled for up to 50 ms.
- Pin, then isolate: `isolcpus` or cpuset partitions, `nohz_full`, interrupt affinity, SMT
  siblings and NUMA locality. Check what was applied; MiniDAQ reports it in `rt_status()`.
- A minor page fault cost about 1.5 µs here, a huge-page fault about 50 µs. Lock memory,
  prefault stacks and buffers by writing, and count faults in tests.
- Event time comes from the hardware; intervals use `CLOCK_MONOTONIC` (28 ns per read here);
  logs use wall-clock time synchronized by NTP or PTP.
- Timer slack (50 µs by default) delays normal threads' wake-ups; real-time threads get none.
  Sleep until absolute deadlines.
- Fixed-memory log-linear histograms record in about 3 ns with under 0.8% error. Measure from
  when data was due, or coordinated omission hides your stalls; this book's own tool had that
  bug.
- Under load, MiniDAQ kept up only with `SCHED_FIFO` on its busy stages; pinning alone made it
  worse, and idle, the real-time throttle made `SCHED_FIFO` worse. Isolate, then prioritize.
- Measure the platform first (cyclictest, with `--policy=other` and no `-p` for the normal
  baseline), then the application at its real rate.

## Further reading {.unnumbered}

- Linux kernel documentation, "Real-Time group scheduling",
  <https://docs.kernel.org/scheduler/sched-rt-group.html>, and "Deadline Task Scheduling",
  <https://docs.kernel.org/scheduler/sched-deadline.html>.
- Linux kernel documentation, "The kernel's command-line parameters" (`isolcpus`,
  `nohz_full`, `rcu_nocbs`, `hugepages`),
  <https://docs.kernel.org/admin-guide/kernel-parameters.html>, and "NO_HZ: Reducing
  Scheduling-Clock Ticks", <https://docs.kernel.org/timers/no_hz.html>.
- Linux kernel documentation, "Transparent Hugepage Support",
  <https://docs.kernel.org/admin-guide/mm/transhuge.html>.
- The Linux Foundation Real-Time Linux project wiki, including the cyclictest documentation,
  <https://wiki.linuxfoundation.org/realtime/start>.
- Manual pages `sched(7)`, `mlock(2)`, `clock_gettime(2)`, `clock_nanosleep(2)`, `prctl(2)`
  (`PR_SET_TIMERSLACK`), `cpuset(7)` and `getrusage(2)`.
- Gil Tene, "How NOT to Measure Latency", talk at Strange Loop 2015 (video), and HdrHistogram,
  <http://hdrhistogram.org/>. The origin of the term coordinated omission and of the histogram
  design used here.
- Gil Tene, `wrk2`, <https://github.com/giltene/wrk2>. A load generator that measures from the
  intended start time.
- Brendan Gregg, *Systems Performance: Enterprise and the Cloud*, 2nd edition, Addison-Wesley,
  2020. Chapters on CPUs, memory and methodology.
- The linuxptp project, <https://linuxptp.sourceforge.net/>, and IEEE 1588-2019, *Standard for a
  Precision Clock Synchronization Protocol for Networked Measurement and Control Systems*.
