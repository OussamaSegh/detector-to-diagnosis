# Profiling and performance engineering {#ch05}

::: box-why
A DAQ engineer is asked to *optimize* software for performance. In a product team that
word has a precise meaning: a change that makes a measured number better, by an amount you can
state with confidence, on the machine the product runs on, without breaking anything else. A
pull request titled "speed up the sorter" with no numbers is an opinion. One that says "the
sort stage went from 37 to 130 M singles/s on the reference PC (10 repetitions each, 95%
interval for the speedup 3.4x to 3.6x), flame graphs attached, regression gate green" is
engineering.
This chapter teaches the second kind: how to measure without fooling yourself, how to find
where the time goes, which compiler and CPU features actually help, and how to keep a win from
quietly disappearing six months later.
:::

**A day in the life.** It is your fourth month. Reconstruction has asked for an energy window
applied on the acquisition PC, so that it receives fewer singles. Two prototypes arrive. One
colleague's uses AVX-512 intrinsics, and their benchmark shows it four times faster than the
plain loop with an `if`. Another colleague's benchmark shows the plain loop just as fast as the
intrinsics. You run both and get both results. The difference is one line: the second benchmark
filters the same 4,096 singles a million times, so the branch predictor has learned which ones
pass, and the plain loop looks faster than it will ever be on real data. With fresh data in
every iteration the plain loop is indeed four times slower, but a branchless loop of three
lines is as fast as the intrinsics, and all of them are limited by memory, not by arithmetic.
You ship the branchless loop, keep the SIMD version behind a run-time check for later, and add
both to the regression gate. The review takes ten minutes, because every claim in it has a
number.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Write micro-benchmarks with Google Benchmark that measure what you think they measure, and
   recognize the classic traps: dead-code elimination, repeated inputs, frequency changes, too
   few repetitions and unpinned threads.
2. Profile a running program with `perf stat`, `perf record` and flame graphs, read the result,
   and know what Intel VTune and AMD uProf add.
3. Use the compiler as a tool: compare `-O2`, `-O3`, `-march`, link-time optimization (LTO) and
   profile-guided optimization (PGO) by measurement, and read the generated assembly.
4. Explain branch prediction and write branchless code; use SIMD for an energy window and know
   when SIMD does not help.
5. Turn measurements into a performance budget, prove that a speedup is real, and run a
   regression gate in CI that fails on a 5% slowdown and does not fail on noise.

## Prerequisites and estimated time {.unnumbered}

Chapters 2 to 4: caches and data layout, the five-stage pipeline, and real-time measurement.
You need `perf` (package `linux-tools` on Ubuntu; on a kernel without a matching package, the
binary from any recent `linux-tools-<version>` directory works) and permission to use it (root,
or `kernel.perf_event_paranoid` at 1 or lower). Reading: about 3 hours. Exercises: 10 to 13
hours. Milestone: 2 hours. In the 10-week schedule this chapter fills week 4.

All numbers in this chapter come from the book's machine described in Chapter 4: a 4-vCPU Intel
Xeon at 2.30 GHz in a Firecracker VM, with AVX2 and AVX-512 (F, BW, VL), Linux 6.18, GCC 13.3
at `-O2` unless stated otherwise, Google Benchmark 1.9.1, single-threaded benchmarks pinned to
CPU 2 with `taskset`, 5 repetitions, median reported. The hypervisor does not expose hardware
performance counters to the VM, which this chapter turns into a lesson: you will see what you
can and cannot learn without them. Every number needs repeating on the acquisition PC
(verify on the acquisition PC).

## Benchmark hygiene

### The intuition

A benchmark is an experiment. It has a hypothesis ("the branchless filter is faster"), a
treatment, a control, sources of noise and ways to be wrong. Most wrong benchmark results are
not caused by bad luck. They are caused by measuring a different thing from the one you meant:
code the compiler deleted, data that is always in cache, a branch predictor that has memorized
the input, a CPU that changed its clock frequency halfway through, or a single run that
happened to be quiet. The cure is a short checklist applied every time, and a habit of asking
"what would the hardware have to be doing for this number to be true?"

### Anatomy of a Google Benchmark

Google Benchmark runs your loop body enough times to get a stable time per iteration, repeats
the whole measurement if you ask, and reports time and any counters you set. Here is the loop of
the energy filter benchmark used throughout this chapter:

```{.cpp include="benchmarks/bm_energy_filter.cpp" snippet="loop"}
```

Four details matter, and each prevents a specific mistake:

- **`benchmark::DoNotOptimize(kept)`** tells the compiler that `kept` is used in a way it cannot
  see, so it must compute it. Without it, an optimizer that can prove the result is unused may
  delete the whole call. The symptom is a benchmark that runs at "0.3 ns per iteration"
  regardless of the input size.
- **`benchmark::ClobberMemory()`** is a compiler barrier: it forces pending writes to memory, so
  the writes to `out` really happen. It costs no instructions; it only stops the compiler from
  reordering or eliding memory accesses across it.
- **A different batch in every iteration.** The pool holds 64 batches of 4,096 singles (4 MiB)
  and the loop walks through them. This is the most important line in the benchmark, as the
  next section shows.
- **`SetItemsProcessed`** (after the loop) makes the benchmark report items per second, which is
  the unit the pipeline's requirements use. Prefer a rate in the unit of the requirement to a
  time per iteration that the reader must convert.

Run benchmarks from a release build, pinned, with repetitions:

```text
taskset -c 2 build/release/benchmarks/bm_energy_filter \
    --benchmark_filter='BM_EnergyFilter/./50/0/4096' --benchmark_repetitions=5
```

With repetitions, Google Benchmark prints each run and then the mean, median, standard
deviation and coefficient of variation (CV). Read the CV first. Below 2% is a quiet benchmark on
this machine; above 5% means either the benchmark or the machine is noisy, and a 5% difference
between two versions means nothing until you have found out which.

### The trap of the repeated input

The energy filter keeps the singles whose energy lies inside a window, for example 400 to
650 keV around the 511 keV photopeak. The obvious implementation has a branch:

```{.cpp include="minidaq/src/processing/energy_filter.cpp" snippet="branchy"}
```

Here is what the benchmark reports when it filters the same batch every iteration, and when it
filters a different one, with energies uniform over 0 to 1,000 keV and the window set so that
50% pass:

| Input, 4,096 singles per iteration | M singles/s, branchy |
|---|---|
| The same batch every iteration | 1,028 |
| A different batch every iteration (64 in turn) | 193 |

A factor of 5.3, from one line of benchmark code. The branch predictor of a modern core keeps a
history of recent branch outcomes and learns patterns over thousands of branches. Filtering the
same 4,096 singles a million times is a pattern it can learn, so the branchy loop almost never
mispredicts. Real data never repeats. The fast number is not a measurement of the filter at all;
it is a measurement of the branch predictor's memory.

The same trap exists for caches (a 64 KiB input that stays in L1 for a million iterations, while
in the pipeline each batch arrives from another core's cache or from memory), for the
allocator (freeing and allocating the same block), and for anything with a lookup table. The
rule: **the benchmark's input must have the statistics and the cache state of the real input**.
For a stream, that means fresh data at the real rate of arrival. Pool many batches and cycle
through them, as above, or generate inputs outside the timed region.

### Frequency, pinning and other noise

A core's clock frequency is not a constant. On bare metal, the CPU raises its frequency when
few cores are busy (turbo) and lowers it when hot or idle (power states), and the operating
system's frequency governor decides how fast to react. A benchmark that starts on an idle core
may spend its first milliseconds at a low frequency. Google Benchmark prints a warning ("CPU
scaling is enabled, the benchmark real time measurements may be noisy") when the governor is not
set to `performance`. On a dedicated benchmark machine:

- **Fix the frequency**: set the governor to `performance` (`cpupower frequency-set -g
  performance`) and disable turbo (on Intel with `intel_pstate`, write 1 to
  `/sys/devices/system/cpu/intel_pstate/no_turbo`). Turbo makes results faster and less
  reproducible; for comparisons, you want reproducible.
- **Pin**: `taskset -c 2` keeps the benchmark on one core, so it is not migrated between cores
  with different cache contents. Choose a core that does not take interrupts (Chapter 4).
- **Disable SMT** or keep the sibling hyperthread idle: a sibling shares the core's execution
  units and caches.
- **Repeat**: at least 5 repetitions for a quick look, 10 or more for a decision, and report the
  median. Benchmark times are skewed (interruptions only ever add time), so the median is more
  robust than the mean.
- **Interleave**: when comparing two builds, alternate their runs (A, B, A, B) rather than
  running all of A and then all of B, so that slow drift (temperature, a background job)
  affects both alike. Within one binary, `--benchmark_enable_random_interleaving=true` does the
  same for the benchmarks it contains.

In a VM, the hypervisor controls frequency, may run other tenants on the same physical core, and
pauses the VM now and then. You cannot fix any of that, so you compensate with more repetitions
and with relative measurements: compare two versions on the same VM in the same session, never a
number from today's VM with one from last week's.

### Other ways to measure the wrong thing

- **`PauseTiming` around small bodies.** Pausing and resuming the timer reads clocks and costs
  far more than a few nanoseconds; Google Benchmark's own documentation calls the pair
  heavyweight. The sort benchmark in this chapter uses it to exclude copying a batch, which is
  acceptable because each sort takes tens of microseconds. For a body of a few nanoseconds, move
  the preparation out of the loop instead.
- **Measuring the debug build**, or a release build with assertions on. Always check the
  configuration line Google Benchmark prints: "Library was built as DEBUG" means the benchmark
  library itself, and your code may be the same.
- **Benchmarking a different machine from the target.** An AVX-512 kernel measured on a laptop
  without AVX-512 measures the fallback.
- **Ignoring the setup.** A benchmark that is 2% of the real workload can be made 10 times faster
  and save 1.8%. Profile the real program first (next section) to find out which benchmarks are
  worth writing.

::: box-mistakes
- **No `DoNotOptimize` on the result.** The compiler deletes the work, and the benchmark reports
  a time that does not depend on the input size.
- **The same input every iteration.** The branch predictor and the caches learn it. Use many
  inputs with the real statistics.
- **One run.** A single run is an anecdote. Five repetitions with the CV is the minimum, and the
  CV tells you whether a difference is meaningful.
- **Comparing numbers from different sessions or machines.** Compare A and B interleaved on one
  machine, in one session.
- **Reporting a time without the machine.** Every published number names the CPU, compiler,
  flags, pinning and repetition count.
:::

## Finding where the time goes: perf and flame graphs

### The intuition

Benchmarks answer "how fast is this piece?" A profiler answers the prior question: "which piece
matters?" A sampling profiler interrupts the program at a fixed rate, for example 999 times per
second, and records where each thread was, including the chain of calls that led there. A
function that appears in 12% of the samples used about 12% of the CPU time. Sampling costs
little, works on the unmodified optimized program, and is statistical: with 10,000 samples, a
function at 12% is known to within about one percentage point, and a function at 0.1% is noise.

### perf stat: counting

`perf stat` runs a command and counts events. On bare metal, the interesting ones come from the
CPU's performance monitoring unit (PMU): cycles, instructions (their ratio, instructions per
cycle or IPC, is the first number to look at), branch misses, cache misses at each level, and
many model-specific events. On the book's VM, the PMU is not exposed:

```text
$ perf stat -- taskset -c 2 build/release/benchmarks/bm_energy_filter \
      --benchmark_filter='BM_EnergyFilter/1/50/0/4096$'
...
 Performance counter stats for 'taskset -c 2 build/release/benchmarks/bm_energy_filter ...':

           1238.87 msec task-clock                #    0.999 CPUs utilized
                 3      context-switches          #    2.422 /sec
                 1      cpu-migrations            #    0.807 /sec
              2274      page-faults               #    1.836 K/sec
   <not supported>      cycles
   <not supported>      instructions
   <not supported>      branches
   <not supported>      branch-misses
```

Software events (task clock, context switches, CPU migrations, page faults) still work, and they
already answer useful questions. Here, one CPU fully used, three context switches in 1.2 seconds,
and a single migration (`taskset` moving itself to CPU 2 before it starts the benchmark) say
that the benchmark ran undisturbed. In general: a stage with thousands of context switches per second is
blocking rather than computing (Chapter 3's channels), and migrations mean a thread was not
pinned. On the acquisition PC, which is not a VM, ask for the hardware events explicitly:

```text
perf stat -e cycles,instructions,branches,branch-misses,cache-references,cache-misses -- cmd
perf stat --topdown -- cmd      # Intel: top-down breakdown, where supported
```

**Top-down analysis** (Yasin's method, used by Intel VTune and by `perf stat --topdown`) sorts
every pipeline slot of the core into four buckets: *retiring* (useful work), *bad speculation*
(work thrown away after a branch misprediction), *front-end bound* (the core is waiting for
instructions) and *back-end bound* (waiting for data or for execution units). It tells you which
kind of fix to try before you try one: a back-end-bound loop does not get faster by removing
branches, and a loop that is 40% bad speculation will not get faster with better data layout.
Bakhvalov's book (Further reading) is the practical reference.

### perf record and perf report: sampling

```text
perf record -e cpu-clock -F 999 -g -- build/profile/minidaq/apps/minidaq_latency --rate 10e6 --seconds 8
perf report --no-children --sort symbol
```

- **`-e cpu-clock`** samples on a software timer. On bare metal, the default event (`cycles`)
  is better because it comes from the PMU and also sees time spent with interrupts disabled; in
  a VM without a PMU, `cpu-clock` is what works.
- **`-F 999`** samples 999 times per second per CPU. An odd rate avoids sampling in lockstep with
  the 1,000 Hz or 250 Hz timer tick.
- **`-g`** records call stacks, which needs a way to walk the stack. The `profile` preset in
  this book's `CMakePresets.json` compiles at `-O2 -g -fno-omit-frame-pointer
  -mno-omit-leaf-frame-pointer`, so `perf` can follow frame pointers: cheap and reliable, at a
  cost of about one register. Alternatives are `--call-graph dwarf` (copies a piece of the
  stack with each sample and unwinds it later from debug information: works without frame
  pointers, with large files and higher overhead) and `--call-graph lbr` (Intel's last branch
  record: accurate, bare metal only).
- **`perf report`** shows functions by sample count. With `--no-children`, each function's
  *self* time (samples in its own code); without it, the *inclusive* time (samples in it or
  anything it called). `perf annotate <function>` shows the samples per instruction, which is
  how you find the one load or branch that costs the time.

Standard libraries are usually built without frame pointers, so stacks through `libstdc++`
may be cut short; the flame graphs below show this as frames whose parent is the library
itself. Ubuntu 24.04 and Fedora 38 and later build their own packages with frame pointers
(verify: for your distribution).

### A flame graph of MiniDAQ

A report is a list; a flame graph is a picture of all the stacks at once. Each box is a
function; its width is the fraction of samples in which it was on the stack; boxes above it are
the functions it called. Colors carry no meaning. You read it by looking for wide boxes, and for
wide *plateaus*: a box with nothing on top of it is a function spending time in its own code.
The script `tools/flamegraph.sh` records with `perf` and renders the graph with Brendan Gregg's
FlameGraph scripts (pinned to a commit):

```text
tools/flamegraph.sh before.svg build/profile/minidaq/apps/minidaq_latency --rate 10e6 --seconds 8
```

![MiniDAQ at 10 M singles/s with the default profile, before the fix (cpu-clock, 999 Hz, 8 seconds, all threads). The source thread and its synthetic generator take about half of all samples; the widest box in the product's own code is `time_order` under the sort stage. The interactive SVG is in `measurements/ch05/flame/`.](src/img/ch05-flame-before.png){width=100%}

Reading it from the bottom, the samples divide by thread:

- **The source thread, 52%.** Most of that is the *synthetic* data generator (27%), and within
  it the standard library's normal and exponential distributions and the Mersenne Twister. The
  generator is test infrastructure, not product code, but it is on the same machine and competes
  for the same cores. Exercise 5.2 has you profile and fix it.
- **The sort stage, 18% inclusive**, of which **`time_order` alone is 11.7% self time**: more than
  the sorting algorithm around it. A comparison of two 64-bit integers should be a few
  instructions inlined into the sort loop. A *function* that is wide in its own right means it
  was called, not inlined, millions of times.
- **Kernel entries and `[vdso]`.** `[vdso]` (12.8% self) is almost entirely the source thread
  reading the clock (`clock_gettime`, which runs in user space through the vDSO) to pace its
  output at 10 M singles/s: a simulator cost again. `finish_task_switch` (14.5% self) is the
  kernel switching threads, spread over the decode, sort, pair and write threads as they block
  and wake on their channels. On four vCPUs that overhead is real, but it belongs to the
  pipeline's synchronization design (Chapter 3), not to a hotspot you fix with a code change.

### The fix: let the compiler inline the comparison

The sort stage called `std::sort(v.begin(), v.end(), time_order)`. Passing a function *by name*
passes a function pointer, and `std::sort`'s comparator type becomes `bool (*)(const Single&,
const Single&)`. Every instantiation of the algorithm with that type is the same code for every
function with that signature, so the comparison is an indirect call unless the optimizer
propagates the constant pointer into the sort and inlines it there. GCC 13 at `-O2` does not.
A lambda or a function object has its *own type*, so the algorithm is instantiated for it and
the call is a direct, inlinable call:

```{.cpp include="minidaq/include/minidaq/pipeline/acquisition_pipeline.hpp" snippet="order"}
```

The benchmark `bm_sort` sorts the same batches three ways (batches as the decoder produces them,
almost in time order, 4,096 singles):

| Comparator (4,096 singles, decoded order) | M singles/s |
|---|---|
| `time_order` (function pointer) | 37.9 |
| Lambda calling `time_order` | 136.5 |
| `TimeOrder{}` (function object) | 117.3 |

The comparator is 3.1 to 3.6 times faster when inlined. The difference between the lambda and
the function object is not meaningful: both are inlined, and across builds the two trade places
(the compiler-flag experiment below shows the lambda varying by more than 20% from build to
build). On shuffled input the gap almost closes (14.3, 18.7 and 19.1 M singles/s), because
then the sort is dominated by mispredicted branches and data movement rather than by the cost of
each comparison. The decoder's output is almost sorted, which is what the pipeline sees, which
is why the benchmark uses it: the benchmark's input has the statistics of the real input.

The pipeline benchmark, before and after one changed line:

| Batch size | Before (median M words/s) | After (min / median / max) |
|---|---|---|
| 64 | (not limited by sort) | 45.7 / 46.7 / 48.5 |
| 512 | (not limited by sort) | 98.0 / 100.0 / 102.3 |
| 4,096 | 33.1 | 79.5 / 84.2 / 87.5 |

Chapter 3 found that batches of 4,096 were the slowest because the sort stage was the
bottleneck. With the comparison inlined, they are 2.5 times faster, and the bottleneck moved:
the flame graph afterwards shows the sort stage at 11.4% inclusive, and batches of 512 are now
fastest. This is the normal course of optimization: fix the top item, profile again, and the
picture changes.

![The same run after the fix. `time_order` is gone as a separate frame (inlined); the sort stage shrank from 18% to 11% of samples.](src/img/ch05-flame-after.png){width=100%}

### VTune and uProf

`perf` is always available and scriptable, which makes it the tool for CI and for remote
machines. Intel VTune Profiler and AMD uProf are free graphical profilers from the CPU vendors.
They add three things worth knowing about: a guided top-down microarchitecture analysis with the
vendor's own event definitions; memory-access analysis that attributes cache misses and memory
bandwidth to source lines and data structures; and threading analysis that shows waits on locks
and condition variables on a timeline. Both need hardware counters, so neither shows more than
`perf` on a VM like the book's. Use VTune on Intel and uProf on AMD; ask which CPU the
acquisition PC uses before you install either.

::: box-mistakes
- **Profiling a debug build.** The profile of unoptimized code has different hotspots. Profile
  the optimized build, with frame pointers and debug information added.
- **Optimizing without profiling.** The function you suspect is rarely the one that is wide.
- **Reading self time as inclusive time, or the reverse.** A wide function with a plateau on top
  is busy itself; a wide function with a tower on top is busy calling others.
- **Too few samples.** A difference of 0.5% between two profiles of 2,000 samples is noise.
  Record long enough to have tens of thousands of samples, or compare with a benchmark.
- **Fixing the test harness and calling it the product.** The synthetic source was the widest
  box, but it does not run on the scanner. Know which boxes are yours.
:::

## The compiler as a tool

### The intuition

The compiler is the largest performance tool you have, and its options are measurable inputs
like any other. `-O2` is the default for release builds in this book: it enables nearly all
optimizations that do not trade code size for speed. `-O3` adds more aggressive inlining, loop
unrolling and vectorization with a more generous cost model (since GCC 12, `-O2` already
vectorizes loops whose cost model says the gain is certain; verify: GCC 12 release notes).
`-march=<cpu>` allows the compiler to use every instruction that CPU has, AVX-512 included.
Link-time optimization (LTO) lets the compiler optimize across translation units, for example
inline a function from `decoder.cpp` into a loop in `pipeline.cpp`. Profile-guided optimization
(PGO) compiles twice: once instrumented, then you run a representative workload, then again with
the recorded branch and call frequencies, so the compiler knows which paths are hot.

None of these is guaranteed to help. Each can make a given loop slower, and the only way to know
is to measure.

### Measured: five builds of the same code

The script `measurements/ch05/flags/run_flags.sh` builds the benchmarks five ways with GCC 13.3
and runs each build twice, interleaved (all five, then all five again), 5 repetitions per run.
Each cell is the median of the 10 runs: in M items/s for `-O2`, and as a ratio to `-O2` for
the others.

| Benchmark | `-O2`, M items/s | `-O3` | `-march=native` | LTO | PGO |
|----------------------------|----------|------|--------------|------|------|
| Decode, 64 Ki words | 330 | 1.32x | 1.50x | 1.52x | 1.41x |
| Energy filter, branchy, 50% | 190 | 0.99x | 0.97x | 0.98x | 1.03x |
| Energy filter, branchless, 50% | 901 | 1.00x | 1.02x | 0.98x | 0.98x |
| Sort, function pointer, 4,096 | 38.8 | **3.28x** | 0.98x | **3.07x** | **3.19x** |
| Sort, lambda, 4,096 | 136 | 0.99x | 0.77x | 0.77x | 0.88x |
| Pipeline, batch 4,096 | 86.4 | 0.92x | 1.03x | 1.04x | 1.07x |

The two rounds agreed within 3% for most cells and within 10% for all; the full table with
both rounds is `measurements/ch05/flags/summary.md`.

What the table says, and what it does not:

- **There is no best setting.** Every option made something faster and something else slower.
  `-O3` made the decoder 32% faster and the whole pipeline 8% slower. `-march=native` and LTO
  made the lambda sort 23% slower, in both rounds.
- **The function-pointer sort is the instructive row.** `-O3`, LTO and PGO all made it about
  3.2 times faster, close to the speed of the lambda: each of them found a way to inline the
  comparator. The likely mechanisms are constant propagation of the pointer into a clone of the
  sort at `-O3` and with LTO, and, with PGO, indirect-call promotion: the profile shows that the
  call always goes to `time_order`, so GCC turns it into a direct, inlinable call (verify: with
  `-fopt-info-ipa` and `-fopt-info-inline`). The source-code fix of the previous section gets the
  same result at `-O2`, without depending on the optimizer's heuristics.
- **Unexplained gains are not gains yet.** The decoder got 1.3 to 1.5 times faster with every
  option. Its loop is in one translation unit with everything it calls inlined from headers, so
  LTO's usual benefit (inlining across files) does not explain it. Plausible causes are loop
  alignment and unrolling, but without hardware counters on this VM that is a hypothesis
  (verify: `perf annotate` and `perf stat` on bare metal). A gain you cannot explain may
  disappear with the next unrelated change.
- **PGO's training matters.** The PGO build was trained on exactly the benchmarks it was then
  measured on, which is the best case. On the real program, train on a recorded acquisition.

MiniDAQ stays at `-O2` without `-march`. The flags are an input to measure again on the
acquisition PC's CPU, not a conclusion to copy.

### Reading the assembly

When a measurement surprises you, read what the compiler produced. Three ways, from quickest to
most precise:

- **Compiler Explorer** (<https://godbolt.org>) compiles a snippet with any compiler and flags
  and colors the assembly by source line. Paste the function, choose GCC 13 with `-O2`, and
  compare with `-O3` side by side. It is the fastest way to answer "does this inline?" or "does
  this vectorize?" and to share the answer in a review.
- **`objdump -d --no-show-raw-insn -C file.o`** shows what is actually in your build, with your
  headers and flags. The branchy filter compiles to two conditional jumps per single, one for
  each half of `e >= lo && e <= hi`:

  ```text
  458:  movss  0xc(%rax),%xmm0      ; load the energy (offset 12 in Single)
  45d:  comiss %xmm2,%xmm0          ; compare with lo
  460:  jb     47b                  ; below lo: skip
  462:  comiss %xmm0,%xmm1          ; compare hi with the energy
  465:  jb     47b                  ; above hi: skip
  ...                               ; copy 16 bytes, ++k
  47b:  add    $0x10,%rax           ; next single
  ```

- **`perf annotate`** shows the same assembly with the profile's samples per instruction.

Ask the compiler to explain itself, too: GCC's `-fopt-info-vec-optimized` and
`-fopt-info-vec-missed` report which loops it vectorized and why not; Clang's
`-Rpass=loop-vectorize` and `-Rpass-missed=loop-vectorize` do the same, and `-Rpass=inline`
reports inlining decisions.

::: box-mistakes
- **`-march=native` in a shipped build.** The binary may crash with an illegal instruction on a
  CPU without the build machine's extensions. Target the acquisition PC's CPU explicitly, or
  build for a baseline and dispatch at run time (next section).
- **Assuming `-O3` is faster.** It is a different trade-off, not a higher setting. Measure.
- **PGO with an unrepresentative training run.** The compiler optimizes for the run you gave
  it. Train on realistic data and rates, and keep the training run in the repository.
- **A PGO profile that silently did not apply.** A profile is found by the object file's path;
  if it is not found, the build proceeds as if there were none. This chapter's first PGO
  measurement had exactly that bug. Check the compiler's `-Wmissing-profile` warnings.
- **Changing flags without re-verifying.** Different flags are a different binary. In a
  regulated product they need the same verification as a code change.
:::

## Branches, branchless code and SIMD

### Branch prediction

A modern core fetches and executes instructions far ahead of the one that is finishing, so it
must guess the direction of every conditional branch long before the condition is known. The
predictor guesses from the branch's history and from the history of recent branches. When it is
right, the branch costs almost nothing. When it is wrong, all the work done along the wrong path
is thrown away, and the core restarts from the branch: a penalty of roughly 15 to 20 cycles on
recent x86 cores (verify: Agner Fog, *The microarchitecture of Intel, AMD and VIA CPUs*, for
your CPU).

A branch on random data is wrong as often as the less likely outcome occurs. The branchy filter
has two branches, `e < lo` and `e > hi`, and with uniform energies the expected number of
mispredictions per single follows from the window:

| Window (keV) | Pass | P(e ≥ lo) | Mispredictions per single (expected) | Branchy, M singles/s | ns per single |
|------------|------|------|--------------|------------|--------|
| 450 to 550 | 10% | 0.55 | about 0.55 | 161 | 6.2 |
| 250 to 750 | 50% | 0.75 | about 0.50 | 193 | 5.2 |
| 50 to 950 | 90% | 0.95 | about 0.10 | 535 | 1.9 |

(Each branch mispredicts with a probability of about the smaller of its two outcome
probabilities: 0.45 + 0.55 × 0.18 for the first row.) Between the 50% and 90% rows, 0.4
mispredictions per single cost 3.3 ns, about 8 ns or 19 cycles at 2.3 GHz per misprediction,
consistent with the published penalty. The 10% window is *slower* than the 50% one even though it
copies fewer singles: what costs time is not the work done for passing singles but the
predictor's uncertainty about which singles pass.

When the input is sorted by energy, the outcomes come in long runs, the predictor is almost
always right, and the branchy loop is the fastest of all (1,121 M singles/s at 10%), because it
also does the least work. Real data is not sorted by energy.

### Branchless code

The branchless version always copies the single and advances the output index only if it
passed:

```{.cpp include="minidaq/src/processing/energy_filter.cpp" snippet="branchless"}
```

`(e >= lo) & (e <= hi)` uses `&`, not `&&`, so both comparisons are always evaluated and there
is no branch to mispredict; the compiler turns the comparisons into flag-setting instructions
and adds the result to `k`. It does more work per single (every single is copied, and the next
copy overwrites a rejected one) and in exchange it runs at the same speed for any input:

| Kernel, M singles/s (4,096 per batch, 64 fresh batches) | 10% | 50% | 90% |
|------------------------------------|-------|-------|-------|
| branchy | 161 | 193 | 535 |
| branchless | 891 | 915 | 940 |
| AVX2 (2 singles per register) | 835 | 835 | 838 |
| AVX-512 (4 singles per register) | 839 | 836 | 839 |

The branchless loop is 4.7 times faster at 50%, and its speed does not depend on the data. For
a DAQ, the second property is worth as much as the first: a stage whose cost depends on the
energy distribution has a latency that depends on the patient.

Branchless code is not always better. It does the work of both paths, so it wins only when the
branch is unpredictable and both paths are cheap. Compilers make this choice themselves for
simple cases (a conditional move, `cmov`), and a profile with hardware counters shows directly
whether a branch mispredicts often. Without counters, as here, the dependence of speed on the
input statistics is the evidence.

### SIMD for the energy window

SIMD (single instruction, multiple data) instructions apply one operation to a whole register
of values: 8 floats in a 256-bit AVX2 register, 16 in a 512-bit AVX-512 register. A filter is a
*compaction*: the output position of each single depends on how many before it passed. Neither GCC 13
nor Clang 18 auto-vectorizes this compaction, at `-O2` or `-O3` ("couldn't vectorize loop" in
GCC's `-fopt-info-vec-missed` report, described below); both vectorize the same loop when it only
*counts* the passing singles, GCC only at `-O3`. Compaction is a case for intrinsics.

A `Single` is 16 bytes (time, crystal, energy), so a 256-bit register holds two singles, and
their energies are float lanes 3 and 7. One comparison per bound gives a mask; `movemask`
extracts the two energy bits; if only the second single passed, swapping the register's halves
moves it to the front; the whole register is stored, and the output index advances by the number
of singles kept:

```{.cpp include="minidaq/src/processing/energy_filter.cpp" snippet="avx2"}
```

The AVX-512 version handles four singles per register and has an instruction made for
compaction, `vpcompressq`, which packs selected 64-bit lanes to the front:

```{.cpp include="minidaq/src/processing/energy_filter.cpp" snippet="avx512"}
```

Both are compiled with `__attribute__((target(...)))`, so the rest of the program stays at the
baseline instruction set, and the library decides once, at run time, which SIMD kernel the CPU
can run:

```{.cpp include="minidaq/src/processing/energy_filter.cpp" snippet="dispatch"}
```

The unit test runs all four kernels on the same inputs (every size from 0 to 37, inclusive
bounds, NaN and infinities, in-place use, an output shorter than the input) and requires
identical output. A SIMD kernel without such a test
is a bug waiting for an unusual input.

Intrinsics are not the only option. `std::experimental::simd` (the Parallelism TS 2, shipped in
libstdc++ since GCC 11) gives portable types such as `native_simd<float>` with masks and
`where` expressions, and a `std::simd` based on it is part of C++26 (verify: P1928 and your
compiler's status page). It is excellent for arithmetic on arrays of floats. It has no portable
compress operation, which is what this filter needs.

### When SIMD does not help

The SIMD kernels are *not faster* than the branchless loop: 835 against 915 M singles/s. Four
reasons, which together answer one of this chapter's check-yourself questions:

1. **The loop is limited by memory traffic, not by arithmetic.** Each single is 16 bytes read and
   up to 16 bytes written. A plain `memcpy` of the same batches (4 MiB, in cache) costs 0.6 ns
   per single on this machine; the branchless filter takes 1.1 ns. There is little arithmetic left to speed up.
2. **The layout wastes lanes.** An array of structures (AoS) puts one energy in every four
   floats, so three quarters of each comparison is spent on time stamps and crystal numbers. To
   see what SIMD can do when the data suits it, a count-only kernel (how many pass, no copy)
   runs at 0.90 ns per single scalar and 0.50 ns with AVX-512, and on a separate array of
   energies (structure of arrays, Chapter 2) it would compare 16 energies per instruction.
3. **The work per element is too small** to pay for the shuffles and mask manipulation that
   compaction needs.
4. **Wide registers can cost frequency.** On some Intel server CPUs, sustained AVX-512 lowers
   the core's clock frequency for all code on that core for a while afterwards (verify: for the
   acquisition PC's CPU; recent generations reduce or remove the effect).

SIMD helps when the data is contiguous and of one type, the work per element is several
operations, and the loop is long. It does not help for short loops, gathers and scatters,
compaction-heavy code on AoS data, or anything limited by memory bandwidth. Measure on 1 Mi
singles (16 MiB, beyond the private caches) and every kernel slows down (branchless 765, AVX-512
733 M singles/s at 50%); on 100 M singles (1.6 GB, Exercise 5.1), branchless and SIMD both run
at about 340 M singles/s, within 3% of each other: the stream from memory, not the instruction
set, sets the speed.

MiniDAQ's default, `FilterKernel::best`, is therefore the branchless kernel on every CPU.
`FilterKernel::simd` selects the widest SIMD kernel the CPU has, through the dispatch above, for
the day the layout changes and SIMD earns its place. The default is a measured decision, and
the comment in `best_kernel()` says so, so that nobody "fixes" it back without measuring.

### Histogramming

The live energy spectrum is a histogram: `++h[code]` for each single's 11-bit energy code. It
looks too simple to optimize, and it has a trap that Exercise 5.4 measures:

| Codes (1 Mi per call) | Simple, G codes/s | Four sub-histograms, G codes/s |
|---|---|---|
| Uniform over 2,048 bins | 2.10 | 2.26 |
| 511 keV photopeak, sigma 25 keV | 2.06 | 2.11 |
| One constant code | 0.41 | 1.24 |

`++h[c]` is a load, an add and a store. When the next code hits the same bin, its load must wait
for the previous store (store-to-load forwarding takes several cycles), so a run of identical
codes becomes one long dependency chain. Four sub-histograms used in turn break the chain into
four independent ones, which the core overlaps:

```{.cpp include="exercises/ch05/e4_energy_spectrum/solution/spectrum.cpp" snippet="split"}
```

A real photopeak spreads over about 50 codes, so both versions run near 2 G codes/s, two hundred
times the scanner's rate. The constant code matters anyway: it is what a stuck channel or a test
pulser produces, which is exactly when the monitoring must not fall behind.

::: box-mistakes
- **Removing a branch that predicts well.** Branchless code does the work of both paths. It
  wins only when the branch is unpredictable.
- **Measuring a branchy kernel on repeated or sorted input.** You measure the predictor.
- **Intrinsics without a scalar reference test.** Test every kernel against the plain version on
  the edge cases: empty input, sizes that are not multiples of the register width, NaN, bounds.
- **SIMD on a memory-bound loop.** Compare with `memcpy` of the same bytes first. If the loop is
  already close, change the layout or the amount of data, not the instructions.
- **Compiling the whole program with `-mavx512f`** to use one kernel. Use the `target`
  attribute and a run-time check, so the program still runs on the CPU without it.
:::

## Performance budgets and regression gates

### A budget per stage

A requirement such as "acquire at 10 M singles/s without loss" becomes testable when you divide
it among the stages. Each stage runs on its own core, so each has 100 ns per single at 10 M
singles/s; a stage that needs more than that falls behind, and one that needs 90 ns has no
margin for the hypervisor, the reconstruction service or a firmware change that doubles the
rate. MiniDAQ's budget, in `docs/performance-budget.md`, lists for each stage its measured cost,
its budget and the benchmark that proves it (the document names the exact benchmark cases):

| Stage | Measured, ns per single | Margin at 10 M/s | Margin at 30 M/s | Benchmark |
|------------------------|------------------|----------|----------|------------------|
| Receive (source) | not yet measured | | | Chapters 9 and 23 |
| Decode | 3.0 | 33x | 11x | `bm_decode` |
| Energy window (branchless) | 1.1 | 90x | 30x | `bm_energy_filter` |
| Sort (batch of 4,096) | 7.4 to 8.5 | 12x | 4x | `bm_sort` |
| Pair | not measured separately | | | `bm_pipeline` only |
| Energy spectrum | 0.44 (0.81 for a constant code) | over 100x | over 40x | Exercise 5.4 |
| Whole pipeline (5 threads, 4 vCPUs) | 11.6 | 8.6x | 2.9x | `bm_pipeline` |

The 30 M singles/s column uses Chapter 2's high-activity estimate (assumption: confirm with
team). Two rows are honest gaps: the receive stage, which Chapter 9 builds and Chapter 23 tunes, and the pair stage,
which has no benchmark of its own, so a regression in it would show only in the whole-pipeline
row. The binding row is the whole pipeline: under 3x margin at the high rate on this VM.

The budget table is a living document: each row has an owner benchmark, and the regression gate
re-measures the benchmarks on every merge request. When a row's margin shrinks below a factor of
two, that is a design discussion, not a surprise during a clinical acquisition.

### How do you prove a speedup is real?

"It got 8% faster" is a statement about two distributions of noisy measurements. To make it a
fact:

1. **Run both versions on the same machine, interleaved, with enough repetitions** (10 or more).
2. **Compare medians**, and give the size of the effect with an interval, not just a point:
   "1.06 to 1.11 times faster (95% confidence)". Exercise 5.5 computes such an interval with a
   bootstrap: resample each side's runs with replacement, recompute the ratio of medians
   thousands of times, and take the percentiles.
3. **Test whether the difference could be noise**. A rank test such as the Mann-Whitney U test
   asks how likely it is that the two sets of runs would be ordered as they are if both came from
   the same distribution. It assumes nothing about the shape of the distributions, which suits
   benchmark times.
4. **Check that the speedup reaches the program.** A kernel 2x faster in a micro-benchmark is
   worth what the profile says that kernel's share is. Re-run the pipeline benchmark and the
   profile.
5. **Explain it.** If you cannot say why it got faster (fewer mispredictions, fewer cache misses,
   an inlined call), you may have measured an accident of code alignment or frequency, and the
   gain may vanish with the next unrelated change.

### The regression gate

Optimizations erode. A refactoring adds a virtual call in the hot loop, an innocent-looking
`std::function` replaces a template, a new log line formats a string per batch. Each costs a few
percent, and nobody notices until the margin is gone. A regression gate in CI catches the
erosion at the merge request that causes it.

The gate has two parts. `tools/perf_suite.sh` runs a short, stable set of benchmarks (decode,
the energy filters, the sort, the histogram and the pipeline) pinned, with 10 repetitions, and
writes one JSON file. `tools/perf_gate.py` compares it with a committed baseline and fails if
any benchmark is more than 5% slower *and* the difference is significant:

```{.python include="tools/perf_gate.py" snippet="compare"}
```

Both conditions are needed. The threshold alone fails at random on a noisy machine; the test
alone flags differences of 0.5% that are real but do not matter. The test is exact (it counts
all orderings of the runs rather than using a normal approximation), which is cheap for 5 to 20
repetitions:

```{.python include="tools/perf_gate.py" snippet="mannwhitney"}
```

The CI job, `.github/workflows/perf.yml`, runs only on a dedicated self-hosted runner labelled
`perf`, with the baseline recorded on that same runner (`benchmarks/baseline/<runner>.json`).
Shared cloud runners are unsuitable: their hardware varies from job to job, and other tenants
share the cores. When an intentional change makes something slower, or the runner's hardware
changes, re-record the baseline in the same merge request, so the review sees it.

On the book's VM, a second run of the suite against the baseline gave speed ratios from 0.952
to 1.025, and the gate passed. The sort came out 4.8% slower: just inside the threshold, and
with p = 0.22, clearly noise. With a threshold alone at 4%, that run would have failed. Then the
sort stage was given the function pointer back, as at tag `ch04`:

```text
benchmark                                     speed        p  verdict
BM_DecodePacked/65536                         1.015   0.9856  ok
BM_EnergyFilter/1/50/0/4096                   1.006   0.7106  ok
BM_EnergyFilter/3/50/0/4096                   0.985   0.0716  ok
BM_HistogramRecord                            1.033   0.9474  ok
BM_Pipeline/4096/64/real_time                 0.381   0.0000  REGRESSION
BM_SortFunctor/4096/0                         0.984   0.0952  ok
```

The pipeline fell to 38% of its baseline speed and the gate failed with exit status 1. The sort
benchmark itself did not notice, because it calls `std::sort` with `TimeOrder{}` directly: a
micro-benchmark protects the code it calls, not the code the product calls. That is why the
pipeline benchmark is in the suite.

::: box-mistakes
- **A gate on shared cloud runners.** The noise is larger than the effects you want to catch.
- **A baseline from another machine.** Compare only with the same runner's own baseline.
- **Gating on a single run, or on the mean.** Use repetitions, medians and a test.
- **Too many gated benchmarks.** Each one costs CI time and is a chance of a false alarm. Gate
  the few that cover the budget table, and run the rest by hand.
- **Silently updating the baseline.** A baseline change is a claim that the slowdown is accepted;
  it belongs in the review, with a reason.
:::

::: box-regulated
Performance is a property the product must keep, so it needs the same discipline as any other
requirement.

- **Performance requirements are requirements.** If the software requirements specification
  states a throughput or latency, each needs a verification method with a pass criterion, an
  environment (the acquisition PC model and configuration) and a record of the result. The
  budget table and the gate are the evidence; keep their raw outputs with the release.
- **Optimizations are changes.** A faster algorithm, a SIMD kernel or a new compiler flag
  changes the binary, so it goes through the same change control, code review and regression
  testing as a feature. A SIMD kernel's equivalence test against the scalar reference is
  verification evidence; keep it in the suite permanently.
- **Compiler and flags are configuration items.** The compiler version, flags (including LTO and
  PGO) and the PGO training data determine the binary. Record them in the build configuration,
  and treat a flag change like a dependency upgrade: justify it, re-run the verification.
- **Determinism versus speed.** Some optimizations change results: `-ffast-math` reorders
  floating-point arithmetic, and a faster random generator changes a simulation's stream. For
  processing that affects image quantification, any such change needs an analysis of its effect
  on the output (Chapter 11), not only a benchmark.
:::

::: box-askteam
1. What throughput and latency requirements does the acquisition software have, in which
   document, and on which reference PC are they verified?
2. Is there a performance test suite or a dedicated benchmark machine today? Who looks at its
   results, and when did it last catch something?
3. Which compiler versions and flags are used for release builds? Is `-march` set, LTO or PGO
   used, and who decides changes to them?
4. Which CPU does the acquisition PC have (vendor, generation, AVX-512 or not), and can we run
   `perf` with hardware counters on a development unit?
5. Where has performance hurt in the past (dropped data, slow start-up, a slow viewer), and was
   the cause found by profiling?
:::

## Exercises {.unnumbered}

**Exercise 5.1 (M): Benchmark three energy-window filters on 100 M singles.** *Goal:* implement
a branchy, a branchless and a SIMD filter, prove that they compute the same result, measure them
on 100 million singles with random and with sorted energies at 10%, 50% and 90% acceptance, and
explain every number. *Starter:* `exercises/ch05/e1_energy_filters/`. *Acceptance:*
`tests/test_filters.cpp` passes (every size from 0 to 40, inclusive bounds, NaN and infinities,
100,000 random singles, all equal to a reference), and `NOTES.md` holds the table from
`bench_filters` with an explanation of the branchy kernel's dependence on acceptance and order,
of SIMD's small gain, and of the bytes per second each kernel moves. *Time:* 3 hours.

**Exercise 5.2 (M): Produce a flame graph of MiniDAQ under load and fix the top hotspot.** *Goal:*
the flame graph above shows the synthetic event source as the widest box. A copy of it,
`ex::EventSource`, is correct and slow (about 53 ns per single). Profile it with
`tools/flamegraph.sh`, find the three widest frames, and make it at least three times faster
without changing its statistics. *Starter:* `exercises/ch05/e2_hotspot/`. *Acceptance:*
`tests/test_event_source.cpp` passes: order and determinism, rate within 1%, pair fraction
within 0.005, energy mean, standard deviation and tail fractions, uniform crystals, and in a
release build at most 18 ns per single (`EX_NS_PER_SINGLE` adjusts the budget for another
machine). `NOTES.md` holds a table of what each change bought. *Time:* 2 to 3 hours.

**Exercise 5.3 (H): Add a CI job that fails if throughput regresses more than 5%.** *Goal:* a
regression gate that fails on a real 5% slowdown and passes on noise: the exact one-sided
Mann-Whitney test, the comparison of medians, and a CI job that runs it on a dedicated runner.
*Starter:* `exercises/ch05/e3_perf_gate/` (Python). *Acceptance:* `tests/test_perf_gate.py`
passes (exact p-values, a clear 10% regression fails, 3% passes, noise is not significant, time
metrics are inverted, missing benchmarks and too few repetitions are reported, exit status), and
your workflow runs the gate against a baseline recorded on the same runner. *Time:* 3 to 4
hours.

**Exercise 5.4 (M, extra): An energy spectrum, fast.** *Goal:* fill a 2,048-bin spectrum from
energy codes, simply and with four sub-histograms, and measure uniform codes, a photopeak and a
constant code. *Starter:* `exercises/ch05/e4_energy_spectrum/`. *Acceptance:*
`tests/test_spectrum.cpp` passes (both versions equal a reference for all sizes, codes are masked
to 11 bits, results accumulate, a bin past 2^32 does not wrap), and your notes explain the
constant-code case. *Time:* 90 minutes.

**Exercise 5.5 (E, extra): Prove a speedup is real.** *Goal:* a percentile-bootstrap confidence
interval for the ratio of medians of two sets of benchmark runs. *Starter:*
`exercises/ch05/e5_speedup_ci/`. *Acceptance:* `tests/test_speedup.cpp` passes: a clear 2x
speedup has a tight interval, no change includes 1, a noisy 5% change with 5 repetitions is not
proven, results are deterministic for a seed and wider at higher confidence, bad input is
rejected. Apply it to two of your own runs from Exercise 5.1. *Time:* 60 minutes.

## MiniDAQ milestone: a benchmark suite and a performance budget {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ has an energy filter with scalar and SIMD kernels chosen at run time, a sort
stage that inlines its comparison, benchmarks for every hot stage, a profiling preset and a
flame-graph script, a performance budget table in the documentation, and a regression gate with
a baseline. **Start:** tag `ch04`. **End:** tag `ch05`.
:::

1. Add `minidaq/include/minidaq/processing/energy_filter.hpp` and
   `minidaq/src/processing/energy_filter.cpp` (four kernels, `kernel_available`, `simd_kernel`, `best_kernel`,
   `filter_energy`), and the unit test `test_energy_filter.cpp`, which compares all kernels on
   edge cases and random data.
2. Add `TimeOrder` to `acquisition_pipeline.hpp` and use it in the sort stage.
3. Add the benchmarks `bm_energy_filter.cpp` and `bm_sort.cpp`.
4. Add the `profile` configure, build and test presets (`-O2 -g -fno-omit-frame-pointer
   -mno-omit-leaf-frame-pointer`) and `tools/flamegraph.sh`.
5. Add `tools/perf_suite.sh`, `tools/perf_gate.py`, `.github/workflows/perf.yml` and a baseline
   for your machine under `benchmarks/baseline/`.
6. Write `docs/performance-budget.md` from your own measurements, with the machine described.
7. Record flame graphs before and after the sort fix and keep them with the raw benchmark JSON
   under `measurements/ch05/`.

**Definition of done.** `ci/run_all.sh` is green on all four presets. `bm_pipeline` at batch 4,096
is at least twice as fast as at tag `ch04` on your machine. `tools/perf_suite.sh` followed by
`tools/perf_gate.py` against your baseline passes, and fails when you put the function-pointer
comparator back. Every row of the budget table names a benchmark. Tag `ch05`.

## Check yourself {.unnumbered}

1. How do you prove a speedup is real? List the steps, and say what each protects against.
2. When does SIMD not help? Give four reasons, with an example of each from this chapter or your
   own work.
3. A benchmark of a branchy loop gets 5 times faster when you change it to process the same
   batch in every iteration. What is happening in the hardware?
4. What do `benchmark::DoNotOptimize` and `benchmark::ClobberMemory` do, and what goes wrong
   without them?
5. In a flame graph, what is the difference between a wide box with a plateau above it and a
   wide box with a tall tower above it? What did the `time_order` box tell you?
6. Why was `std::sort(v.begin(), v.end(), time_order)` three times slower than the same sort with
   a lambda? Why did `-O3` remove most of the difference?
7. The branchy filter is slower at 10% acceptance than at 50%, although it copies fewer singles.
   Why?
8. Why should a shipped binary not be compiled with `-march=native`, and how do you still use
   AVX-512 where the CPU has it?
9. A regression gate compares a merge request's benchmark run with a baseline. Why does it need
   both a threshold and a statistical test, and why must the baseline come from the same machine?
10. Filling a histogram with one constant code is five times slower than with uniform codes. Why,
    and how do sub-histograms fix it?
11. Your VM reports `cycles <not supported>`. Name three things you can still learn with `perf`,
    and one thing you cannot.

## Summary {.unnumbered}

- A benchmark is an experiment. Keep results alive with `DoNotOptimize`, give it fresh inputs
  with the real statistics, pin it, repeat it, report the median and the CV, and name the
  machine.
- The same batch in every iteration made a branchy filter look 5.3 times faster than it is: the
  branch predictor learned the input.
- Profile before you optimize. A flame graph of MiniDAQ showed `time_order` at 11.7% self time:
  a comparator passed as a function pointer and never inlined. A function object made the sort
  3 times faster and the pipeline 2.5 times faster at batches of 4,096.
- Without hardware counters (a VM), `perf` still samples with `cpu-clock` and counts software
  events. On the acquisition PC, use cycles, instructions, branch and cache misses, and top-down
  analysis.
- Compiler flags are measurable inputs, not settings to copy. `-O3`, LTO and PGO each made one
  benchmark 1.3 to 3.3 times faster and another up to 23% slower. Fix the source when you can.
- A misprediction cost about 8 ns (19 cycles) here. Branchless code ran at 0.9 G singles/s for any
  acceptance, 4.7 times the branchy loop at 50%, and made the stage's cost independent of the
  data.
- SIMD did not beat the branchless loop: the filter is memory-bound and the AoS layout wastes
  three quarters of each register. SIMD needs contiguous, homogeneous data and enough work per
  element.
- Use intrinsics behind `target` attributes with run-time dispatch, and test every kernel against
  the scalar one.
- A performance budget per stage, each row backed by a benchmark, turns a throughput requirement
  into something testable. A gate with a 5% threshold and a significance test keeps it.

## Further reading {.unnumbered}

- Denis Bakhvalov, *Performance Analysis and Tuning on Modern CPUs*, second edition, 2024, free
  online at <https://github.com/dendibakh/perf-book>. The practical reference for this chapter:
  measurement, `perf`, top-down analysis, and CPU-specific tuning.
- Agner Fog, *Software optimization resources*, <https://www.agner.org/optimize/>, in particular
  *Optimizing software in C++* and *The microarchitecture of Intel, AMD and VIA CPUs* (branch
  prediction and misprediction penalties per core).
- Brendan Gregg, "Flame Graphs", <https://www.brendangregg.com/flamegraphs.html>, and the
  FlameGraph scripts, <https://github.com/brendangregg/FlameGraph>; and *Systems Performance*,
  second edition, Addison-Wesley, 2020.
- Google Benchmark user guide, <https://github.com/google/benchmark/blob/main/docs/user_guide.md>.
- The `perf` wiki, <https://perfwiki.github.io/>, and `man perf-record`, `man perf-stat`.
- Daniel Lemire, "Fast Random Integer Generation in an Interval", *ACM Transactions on Modeling
  and Computer Simulation* 29(1), 2019 (the multiply-shift reduction in Exercise 5.2).
- David Blackman and Sebastiano Vigna, "Scrambled Linear Pseudorandom Number Generators", *ACM
  Transactions on Mathematical Software* 47(4), 2021 (xoshiro256\*\*).
- Ahmad Yasin, "A Top-Down Method for Performance Analysis and Counters Architecture", ISPASS
  2014.
- Intel Intrinsics Guide, <https://www.intel.com/content/www/us/en/docs/intrinsics-guide/>.
- Matt Godbolt, Compiler Explorer, <https://godbolt.org>.
