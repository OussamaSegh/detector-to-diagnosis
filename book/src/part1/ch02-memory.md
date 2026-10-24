# Memory, caches and data-oriented design {#ch02}

::: box-why
The role asks for C++ "for a continuous stream of detector data".
At tens of millions of events per second, arithmetic is almost free and memory is
everything: one cache miss to DRAM costs as much time as a few hundred additions. The DAQ
lead is the person who decides how events are laid out in memory, on the wire and on
disk, and those decisions are expensive to change once firmware, files and analysis code
depend on them.
:::

**A day in the life.** The physics team wants to add a "pile-up flag" and a depth-of-interaction
estimate to every single. A colleague opens a merge request that adds a `bool` and a
`float` to the `Single` struct. The unit tests pass. You run the throughput benchmark
before approving and see the sorter drop from 41 to 33 million singles per second. The
struct grew from 16 to 24 bytes (the `bool` dragged in padding), so four singles per cache
line became two and two-thirds, every stage moves 50% more bytes, and the pipeline crossed
the point where the sorter's working set no longer fits in L2. You propose a different
layout: keep the hot 16-byte record and store the rarely used fields in a parallel "cold"
array. This chapter gives you the numbers to make that argument.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Estimate the memory bandwidth and cache footprint of an event stream from its rate and
   record size, and say which level of the memory hierarchy each pipeline stage works in.
2. Lay out data as an array of structures (AoS) or a structure of arrays (SoA), split hot
   from cold fields, and justify the choice with a measurement.
3. Remove heap allocation from a hot loop using pre-allocated buffers, object pools and
   `std::pmr` arenas, and prove with a test that the steady state does not allocate.
4. Pack event records into 64-bit words that match a hardware or file format, with
   explicit byte order, using `std::bit_cast`, shifts and masks.
5. Recognize false sharing in code and in a profile, and remove it.

## Prerequisites and estimated time {.unnumbered}

Chapter 1 (strong types, `Single`, the build). Basic knowledge of what a CPU cache is.
Reading: about 3 hours. Exercises: 5 to 6 hours. Milestone: 2 hours. Week 1 of the
schedule.

## The memory hierarchy in numbers

### The intuition

A modern core can retire several instructions per cycle, but only if the data is close. Data
lives in a hierarchy of memories, each larger and slower than the one above it. The CPU
moves data between levels in fixed-size blocks called [cache lines]{.idx key="cache line"},
64 bytes on every current x86-64 and most ARM server cores. When you read one byte, the
whole 64-byte line containing it comes in. When you write one byte, the core must own the
whole line.

Everything in this chapter follows from three facts: lines are 64 bytes, each level is
roughly three to ten times slower than the one above, and the hardware is very good at
predicting sequential access and very bad at predicting random access.

### Measure it yourself

Published latency tables are a good start, but the numbers that matter are the ones on your
machine. MiniDAQ's `bm_latency` benchmark measures load latency with a *pointer chase*:
each node holds the address of the next one in a random cyclic order, so every load must
wait for the previous one and the prefetchers cannot help.

```{.cpp include="benchmarks/bm_latency.cpp" snippet="chase"}
```

On the machine used for this book (a 4 vCPU cloud VM on an Intel Xeon at 2.30 GHz,
GCC 13.3, `-O2`, mean of three runs, reproducible with
`build/release/benchmarks/bm_latency --benchmark_repetitions=3`):

| Working set | Where it lives (this machine) | Measured latency per load | Cycles at 2.3 GHz |
|---|---|---|---|
| 16 KiB | L1 data cache (48 KiB) | 1.7 ns | about 4 |
| 512 KiB | L2 (2 MiB per core) | 5.9 ns | about 13 |
| 8 MiB | L3 (shared) | 36 ns | about 83 |
| 64 MiB | L3 slices far away, partly DRAM | 138 ns | about 320 |
| 1 GiB | DRAM, plus TLB misses | 204 ns | about 470 |

Two things stand out. First, the ratio between the fastest and slowest row is over 100.
A loop that misses to DRAM on every event can process at most about five million events
per second on one core, whatever its arithmetic does. Second, the L3 on this large server
part is slow (tens of nanoseconds), because it is a big mesh shared by many cores; on a
desktop CPU with a small L3, expect 10 to 15 ns. Your acquisition PC's numbers will differ;
run the benchmark on it in your first weeks.

### Bandwidth, prefetching and why sequential access is cheap

Latency is the cost of one isolated miss. Streaming access is different: the hardware
prefetchers see a sequential (or constant-stride) pattern and fetch lines ahead of use, and
the core keeps many misses in flight at once. A single core can typically stream 10 to 20
GB/s from DRAM, and a socket several times that. That is why the `Single` stream of a DAQ,
which is mostly read sequentially, is cheap to pass through a stage, while a hash table of
per-crystal state that is accessed randomly is expensive.

Rule of thumb: **sequential bytes are cheap, random lines are expensive.** Count both when
you design a stage.

### The TLB and huge pages

Virtual addresses are translated to physical ones through page tables, and the translation
lookaside buffer ([TLB]{.idx key="TLB (translation lookaside buffer)"}) caches recent
translations. With 4 KiB pages, a first-level data TLB of 64 entries covers only 256 KiB.
A random access over 1 GiB misses the TLB almost every time and pays a page walk on top of
the cache miss, which is part of why the last row of the table above is slower than the
one before it. Huge pages (2 MiB on x86-64) make each TLB entry cover 512 times more
memory. Chapter 4 shows how a DAQ allocates its big ring buffers on huge pages, with
`madvise(MADV_HUGEPAGE)` or explicitly reserved hugetlbfs pages.

### Putting a stream into numbers

Exercise 2.1 asks you to do this by hand; here is the template you will reuse for every
design discussion. A NeuroLF-class scanner at high activity might produce 30 million
singles per second (*assumption: confirm with team*; the real number depends on activity,
geometry and thresholds).

| Record | Bytes per single | Stream rate | Per pipeline pass (read + write) | Per hour on disk |
|---|---|---|---|---|
| Packed word (MDQ-P1) | 8 | 240 MB/s | 480 MB/s | 0.86 TB |
| `minidaq::Single` | 16 | 480 MB/s | 960 MB/s | 1.7 TB |

Neither rate stresses DRAM bandwidth. What stresses the system is *how* the data is
touched: a sorter that keeps a time window of singles, a histogram with one bin per crystal
pair, a per-crystal calibration lookup. Those have working sets, and the question is always
"does the working set fit in L1, L2 or L3?".

How many singles fit in a cache line? With 16-byte singles, four; with 8-byte packed words,
eight. A coincidence window of 10 ns at 30 Msingles/s contains on average 0.3 singles, so the
sorter's active window is tiny; but a sorter that merges 72 board streams keeps 72 input
cursors and 72 partially filled buffers hot, which is where L1 starts to matter (Chapter 10).

::: box-mistakes
- Quoting average throughput and ignoring that a stage's random accesses decide its speed.
- Benchmarking with a data set that fits in L2 and deploying with one that does not.
- Assuming the acquisition PC has the same caches as your laptop.
:::

## AoS, SoA, hot and cold data

### The intuition

An array of structures (AoS) stores each event's fields together:
`time crystal energy | time crystal energy | ...`. A structure of arrays (SoA) stores each
field in its own array: `time time time ... | crystal crystal ... | energy energy ...`.
Neither is better in general. The right layout is the one where **each pass over the data
reads only the bytes it needs, sequentially**.

```{.dot caption="Array of structures versus structure of arrays for four singles. A pass that needs only energies (green) streams through every byte of the AoS layout but only through the energy array of the SoA layout." width="95%"}
digraph G {
  node [shape=plaintext, fontname="Helvetica", fontsize=11]; edge [style=invis]; rankdir=TB;
  aos [label=<<table border="0" cellborder="1" cellspacing="0" cellpadding="5">
    <tr><td colspan="12" align="left"><b>AoS: std::vector&lt;Single&gt;, 16 bytes per single, 4 per cache line</b></td></tr>
    <tr><td bgcolor="#cfe0f3">time 0</td><td bgcolor="#f3e3cf">crystal 0</td><td bgcolor="#cfeccf">energy 0</td>
        <td bgcolor="#cfe0f3">time 1</td><td bgcolor="#f3e3cf">crystal 1</td><td bgcolor="#cfeccf">energy 1</td>
        <td bgcolor="#cfe0f3">time 2</td><td bgcolor="#f3e3cf">crystal 2</td><td bgcolor="#cfeccf">energy 2</td>
        <td bgcolor="#cfe0f3">time 3</td><td bgcolor="#f3e3cf">crystal 3</td><td bgcolor="#cfeccf">energy 3</td></tr></table>>];
  soa [label=<<table border="0" cellborder="1" cellspacing="0" cellpadding="5">
    <tr><td colspan="4" align="left"><b>SoA: one array per field</b></td></tr>
    <tr><td bgcolor="#cfe0f3">time 0</td><td bgcolor="#cfe0f3">time 1</td><td bgcolor="#cfe0f3">time 2</td><td bgcolor="#cfe0f3">time 3</td></tr>
    <tr><td bgcolor="#f3e3cf">crystal 0</td><td bgcolor="#f3e3cf">crystal 1</td><td bgcolor="#f3e3cf">crystal 2</td><td bgcolor="#f3e3cf">crystal 3</td></tr>
    <tr><td bgcolor="#cfeccf">energy 0</td><td bgcolor="#cfeccf">energy 1</td><td bgcolor="#cfeccf">energy 2</td><td bgcolor="#cfeccf">energy 3</td></tr></table>>];
  aos -> soa;
}
```

### Measured: summing energies over 100 million singles

The benchmark `bm_layout` sums the energy of every single, once from a `std::vector<Single>`
(16 bytes per event) and once from a separate `std::vector<float>` of energies (4 bytes per
event):

```{.cpp include="benchmarks/bm_layout.cpp" snippet="sum"}
```

Results on the book's machine (GCC 13.3, `-O2`, mean of three repetitions):

| Benchmark | 64 Ki singles (1 MiB, in L2) | 100 M singles (1.6 GB, DRAM) |
|---|---|---|
| Sum energies, AoS | 45 µs (1.45 G singles/s) | 198 ms (508 M singles/s, 7.6 GiB/s) |
| Sum energies, SoA | 44 µs (1.50 G singles/s) | 84 ms (1.19 G singles/s) |
| Gate on all fields, AoS | | 277 ms (362 M singles/s) |
| Gate on all fields, SoA | | 161 ms (625 M singles/s) |

Read the table the way you would read it in a design review:

- **In cache, layout does not matter here.** Both versions run at about 1.5 billion singles
  per second; the loop is limited by the chain of dependent `double` additions (each add
  must wait for the previous one; GCC will not reorder floating-point additions without
  `-ffast-math`).
- **From DRAM, SoA is 2.3 times faster**, because it reads 4 instead of 16 bytes per
  event. The gap is less than 4x because at 1.2 billion singles per second the SoA loop is
  again close to the arithmetic limit.
- **When a pass needs every field, the advantage shrinks** but did not vanish on this
  machine. I first assumed the SoA loop had been vectorized; `g++ -O2
  -fopt-info-vec-optimized` showed that neither loop was. The VM does not expose hardware
  counters, so the remaining difference is not explained here; Exercise 2.2 asks you to
  measure it with `perf stat` on real hardware. Check an explanation with a tool before
  you write it in a report.

### Hot/cold splitting

Real event records carry fields of very different importance. A sorter needs time, crystal
and energy for every single; a pile-up flag or a raw ADC value is read by a calibration
job once a week. Putting them in the same struct makes every pass pay for every field.
Hot/cold splitting keeps the fields every pass needs in a compact struct and moves the rest
to a parallel array indexed the same way (or drops them before the hot path entirely):

```cpp
struct SingleHot { Picoseconds time; CrystalId crystal; KeV energy; };   // 16 B
struct SingleCold { std::uint16_t adc_raw; std::uint8_t flags; };        // rarely read
std::vector<SingleHot> hot;    // the sorter streams through this
std::vector<SingleCold> cold;  // same index; read only by QC and calibration
```

### Alignment, padding and alignas

Every type has an alignment requirement, and the compiler inserts padding so that each
member is aligned and the struct's size is a multiple of its alignment. Exercise 2.6 shows a
status struct that wastes 19 of its 40 bytes on padding because of member order. The rule
that fixes almost every case: **order members from largest to smallest alignment**. Verify
with `static_assert(sizeof(T) == N)` in the header, so the next person who adds a field
sees the consequence at compile time, as MiniDAQ does for `Single`.

`alignas(N)` raises a type's or variable's alignment. You need it for three things in a
DAQ: to put per-thread data on separate cache lines (false sharing, below), to align buffers
for SIMD loads (Chapter 5) and to satisfy DMA or hardware requirements (Chapter 22).

::: box-mistakes
- Adding a `bool` to a hot struct without checking `sizeof`.
- Converting to SoA for a single pass that needs every field anyway.
- Sending a struct with padding over the network with `memcpy` (padding bytes have
  unspecified values and the layout is ABI-specific).
:::

## Allocation strategies: keeping the heap out of the hot path

### The intuition

`new` and `delete` (and `malloc`, which they usually call) are general-purpose: they handle
any size, any lifetime, any thread. That generality costs a lock or per-thread cache
lookup, occasional system calls (`brk`, `mmap`) to get memory from the kernel, and page
faults when that memory is first touched. None of it is slow on average. All of it is
unpredictable, and the slow cases arrive exactly when the system is busiest. A real-time
pipeline therefore allocates everything it needs at start-up and recycles it.

### Three patterns

**Pre-allocate and reuse.** The simplest and most common: a buffer created once, cleared
per batch. `std::vector::clear()` keeps the capacity, so after the first batch `push_back`
never allocates. Reserve the maximum capacity at start-up and the first batch is
allocation-free too.

**Object pools.** A fixed array of objects plus a free list. Pipeline stages pass
*indices* or pointers into the pool instead of allocating buffers; the last stage returns
the buffer to the pool. Chapter 3's pipeline uses a pool of fixed-size batches that cycle
from receiver to writer and back.

**Arenas with `std::pmr`.** The polymorphic memory resources in `<memory_resource>` (C++17)
let standard containers allocate from a resource you choose:

- `std::pmr::monotonic_buffer_resource` allocates by bumping a pointer through a buffer
  and frees nothing until it is reset or destroyed. Perfect for "build some temporary
  containers per batch, throw them all away at the end".
- `std::pmr::unsynchronized_pool_resource` and `synchronized_pool_resource` keep pools of
  fixed-size blocks, for many small objects with individual lifetimes.
- `std::pmr::null_memory_resource()` throws on every allocation. As the upstream of an
  arena, it turns "the arena was too small" into an error instead of a silent `malloc`.

```{.cpp include="benchmarks/bm_alloc.cpp" snippet="pmr"}
```

### Measured, and what the measurement says

`bm_alloc` filters 64 batches of 4,096 singles three ways:

| Variant | Time for 262,144 singles | Throughput |
|---|---|---|
| New `std::vector` per batch | 1.84 ms | 144 M singles/s |
| `pmr::monotonic_buffer_resource` per batch | 1.62 ms | 165 M singles/s |
| One reused `std::vector` (`clear()` per batch) | 1.66 ms | 159 M singles/s |

The arena is about 12% faster than allocating per batch, and about the same as simply
reusing a vector. That is an honest and useful result: glibc's allocator is very fast for a
repetitive pattern of same-sized allocations, so the *average* cost of allocation here is
small. The reasons to remove allocation from the hot path are about the *worst* case:
a `malloc` that needs to call `mmap`, a first touch of a new page that costs a page fault
(several microseconds), a lock contended by another thread. Chapter 4 measures those as
tail latency. The habit to build: **allocate at start-up, recycle in the loop, and prove it
with a test.**

### Proving a loop does not allocate

A claim like "the decoder never allocates" belongs in a test, not a comment. MiniDAQ has a
separate test binary that replaces the global `operator new` with a counting version and
asserts that decoding 100,000 words performs zero allocations:

```{.cpp include="minidaq/tests/unit/test_zero_alloc.cpp" snippet="test"}
```

The test is not built under AddressSanitizer, which installs its own allocator. If someone
later adds a `std::string` or a `std::vector` to the decoder's hot path, this test fails and
names the problem.

## Bit-level packing: 64-bit event words

### The intuition

Front-end electronics do not send C++ structs. They send words: fixed-size groups of bits
with fields at defined positions, chosen to fit the most information into the fewest bytes
of link bandwidth. The DAQ decodes those words, and often stores its own output in a packed
format as well. Getting bit positions, byte order and rollover right is a large part of the
real DAQ work, and the bugs are subtle (a time field one bit too short works for 0.7 seconds
and then wraps).

### MiniDAQ's packed single, MDQ-P1

```{.dot caption="The MDQ-P1 packed single: 15-bit crystal id, 11-bit energy in 0.5 keV steps, and a 38-bit time counter in 5 ps steps split into a 28-bit coarse part (5.12 ns ticks) and a 10-bit fine part."}
digraph G {
  node [shape=record, fontname="Helvetica", fontsize=10];
  w [label="{63 .. 49|crystal (15)} | {48 .. 38|energy (11)\n0.5 keV/LSB} | {37 .. 10|coarse (28)\n5.12 ns/LSB} | {9 .. 0|fine (10)\n5 ps/LSB}"];
}
```

```{.cpp include="minidaq/include/minidaq/format/packed_single.hpp" snippet="layout"}
```

The design choices, each of which you should be able to defend in a review:

- **15 bits of crystal id** cover 32,768 crystals; MiniDAQ's reference scanner has 18,432.
- **0.5 keV energy steps up to 1023.5 keV.** Detector energy resolution is around 10%
  (about 50 keV FWHM at 511 keV), so the quantization is a hundred times finer than the
  physics. Energies above the range saturate to the maximum code rather than wrapping
  (which would turn a 1,100 keV event into a 76 keV one).
- **A 38-bit time counter in 5 ps units.** This is a coarse counter of 5.12 ns ticks (a
  195.3125 MHz clock, *assumption: confirm with team*) with a 10-bit fine interpolation, so
  coarse and fine together form one binary counter. It wraps every
  $2^{38} \times 5\,\text{ps} = 1.374$ s, so the decoder must reconstruct absolute time.

### Shifts and masks, not bit-fields

C++ has bit-fields (`std::uint64_t crystal : 15;`), and they look like the obvious tool. Do
not use them for formats. The order in which bit-fields are allocated within a unit, and
whether a field may straddle units, are implementation-defined; so is the layout of the
bytes in memory. A bit-field struct is a statement about one compiler's ABI, not a format
specification. Shifts and masks operate on *values*, so the same code gives the same result
on every compiler and every host:

```{.cpp include="minidaq/include/minidaq/format/packed_single.hpp" snippet="codec"}
```

These functions are `constexpr`, so tests can check them with `static_assert`, and they
compile to a handful of shift and AND instructions.

### Byte order

The value of a 64-bit word is independent of byte order; its *representation in memory or
on the wire* is not. MiniDAQ defines all wire and file formats as little-endian, which is
the native order of x86-64 and of ARM in its usual configuration, so the conversion is a
no-op on every machine you will use, and the code is still correct on a big-endian host.
The helpers from Chapter 1 do the conversion; `std::byteswap` is the C++23 standard
version, and `std::endian::native` (C++20) tells you the host order at compile time.

To reinterpret bits between types (a `float`'s bits as a `uint32_t`), use
`std::bit_cast<std::uint32_t>(f)` (C++20): it is `constexpr`, well-defined, and compiles to
nothing. `reinterpret_cast` between unrelated types, and type punning through a `union`,
are undefined behavior in C++ (the union trick is allowed in C, not in C++).

### Rollover: getting absolute time back

The decoder sees a 38-bit counter that wraps every 1.374 s. Absolute time is reconstructed
by counting wraps: if a new value is much smaller than the last one, the counter wrapped.
"Much smaller" needs a definition, because streams from real hardware are only
*approximately* ordered. MiniDAQ uses half the wrap period as the threshold: a backwards
jump of more than 0.69 s is a wrap, a smaller one is a slightly late word.

```{.cpp include="minidaq/include/minidaq/format/packed_single.hpp" snippet="unwrap"}
```

The unit tests drive this through twenty wraps and through the nasty case of a word stamped
just before a wrap that arrives just after it. Chapter 9 adds explicit time markers from
the hardware, which make the reconstruction robust against long gaps (a lost burst of
packets longer than half a period would otherwise silently shift time by 1.374 s).

### The zero-allocation decoder

The decoder writes into storage the caller provides, so it never allocates, and it counts
words it cannot use instead of throwing:

```{.cpp include="minidaq/src/format/packed_single.cpp" snippet="decode"}
```

On the book's machine it decodes about 260 to 320 million words per second on one core
(`bm_decode`: 4 Mi words in 16.0 ms; 64 Ki words, which fit in L2, in 0.20 ms). At 30
million singles per second that is about 10% of one core, leaving the budget for sorting.

::: box-mistakes
- Using C++ bit-fields to describe a wire format.
- Letting an out-of-range value wrap into a field instead of saturating or rejecting it.
- Forgetting that a narrow time field wraps, or testing only within the first wrap period.
- `reinterpret_cast`ing a byte buffer to `std::uint64_t*`.
:::

## False sharing

### The intuition

Cache coherence works on lines, not variables. If thread A writes variable `a` and thread B
writes variable `b`, and `a` and `b` are in the same 64-byte line, each write forces the
line to move from one core's cache to the other's. Logically the threads share nothing;
physically they fight over one line. That is [false sharing]{.idx}, and it is common in
exactly the code a DAQ lead writes: per-stage statistics counters, per-thread histograms,
the head and tail indices of a queue.

### Measured

`bm_false_sharing` lets two threads each increment their own atomic counter one million
times, once with the two counters adjacent (same line) and once padded to separate lines:

```{.cpp include="benchmarks/bm_false_sharing.cpp" snippet="counters"}
```

| Layout | 1 thread | 2 threads (each its own counter) |
|---|---|---|
| Same cache line | 6.2 ms | 36.1 ms |
| Padded to separate lines | 5.9 ms | 5.9 ms |

Same work per thread, six times slower, with no data shared at all. With more threads and
cores on different sockets the penalty grows.

### Why std::hardware_destructive_interference_size exists, and why MiniDAQ does not use it

C++17 added `std::hardware_destructive_interference_size` (in `<new>`) as the portable name
for "the distance that keeps two objects from false sharing". In practice it is awkward:
GCC provides it but warns when it is used in a header (`-Winterference-size`), because its
value can change with `-mtune` and would then silently change struct layouts between
translation units, an ABI hazard; Clang with libstdc++ does not provide it before Clang 19.
MiniDAQ uses a named constant of 64 bytes and a small wrapper:

```{.cpp include="minidaq/include/minidaq/core/cache.hpp" snippet="padding"}
```

On x86, Intel's adjacent-line prefetcher fetches lines in pairs, so 128 bytes of separation
is safer still when memory is not tight; Apple's M-series cores have 128-byte lines.

### How to spot it

In code review: any array or struct holding mutable per-thread data, or two atomics
written by different threads declared next to each other. In a profile: an innocent-looking
increment or store that takes hundreds of cycles; on bare metal Linux, `perf c2c record`
followed by `perf c2c report` lists cache lines with "HITM" (hit in another core's
modified line) accesses and the offsets touched within each line. If two threads touch
different offsets of the same line, you have false sharing.

::: box-regulated
Memory layout decisions become regulated artifacts in two ways.

- **Formats are interfaces.** MDQ-P1 is used by the decoder, the list-mode writer and the
  Python analysis. In a 62304 project its specification is a controlled document (part of
  the software architecture or an interface control document, Chapter 24), with a version
  number, and every change goes through change control with an impact analysis
  (Chapter 16). The `static_assert`s and round-trip tests are the verification evidence.
- **Quantization and saturation are risk-relevant.** An energy that wraps instead of
  saturating, or a time field that wraps without detection, would silently corrupt data
  that feeds quantitative images. List them as potential causes in the hazard analysis
  (Chapter 15) and point to the tests that verify the controls (saturation test,
  multi-wrap unwrapping test).
- **Performance claims need evidence.** If the software requirements state a throughput
  (Chapter 14), the benchmark that demonstrates it, with machine and compiler recorded, is
  part of the verification record.
:::

::: box-askteam
1. What is the exact word format the front-end boards send, who owns its specification,
   and how is it versioned?
2. How is time represented end to end (clock frequency, coarse/fine split, rollover
   period), and where is absolute time reconstructed?
3. What is the peak singles rate per board and for the whole scanner, and what record size
   does the acquisition PC handle internally?
4. What are the acquisition PC's CPU model, cache sizes, memory channels and NUMA
   layout?
5. Has anyone profiled the DAQ for cache misses or false sharing, and are those results
   kept anywhere?
:::

## Exercises {.unnumbered}

**Exercise 2.1 (E): How many bytes per second?** *Goal:* compute bytes/s, GiB/s and Gbit/s
for 30 M singles/s at 8, 12 and 16 bytes per single, and singles per cache line; interpret
each number for the network, memory and disk. *Starter:*
`exercises/ch02/e1_stream_budget/`. *Acceptance:* `tests/test_budget.cpp` passes and
`ANSWER.md` explains what each rate means. *Time:* 30 minutes.

**Exercise 2.2 (M): AoS vs SoA on 100 M events.** *Goal:* implement the conversion and both
sums, benchmark them on 100 million singles and explain the gap with bytes per event and,
on bare metal, `perf stat` cache-miss counts. *Starter:* `exercises/ch02/e2_aos_soa/`.
*Acceptance:* correctness tests pass; your log records the two timings and the cache-miss
ratio. *Time:* 60 to 90 minutes.

**Exercise 2.3 (M): Take the heap out of the event loop.** *Goal:* make a filter stage
allocation-free in the steady state with a `std::pmr::monotonic_buffer_resource`, and
reject batches above capacity. *Starter:* `exercises/ch02/e3_pmr_arena/`. *Acceptance:*
1,000 batches after warm-up cause zero calls to global `operator new` (the test counts
them); oversized batches return `batch_too_large`. *Time:* 60 minutes.

**Exercise 2.4 (H): Design a 64-bit packed single.** *Goal:* a 64-bit word with crystal,
coarse time, fine time and energy, encode/decode functions and a design note justifying
every field width. *Starter:* `exercises/ch02/e4_packed_word/`. *Acceptance:* fields do not
overlap, 200,000 random singles round-trip within quantization, bytes are little-endian.
*Time:* 2 hours.

**Exercise 2.5 (M, extra): Per-stage counters without false sharing.** *Goal:* lay out
per-stage counters so that no two stages share a cache line, and measure the speedup.
*Starter:* `exercises/ch02/e5_false_sharing/`. *Acceptance:* counters of different stages
are at least 64 bytes apart; concurrent increments are exact. *Time:* 45 minutes.

**Exercise 2.6 (E, extra): Shrink a struct by reordering its fields.** *Goal:* reduce a
40-byte status struct to 24 bytes by reordering members only, and account for every padding
byte. *Starter:* `exercises/ch02/e6_struct_layout/`. *Acceptance:* `sizeof <= 24`, same
member types, trivially copyable. *Time:* 20 to 30 minutes.

## MiniDAQ milestone: packed format and zero-allocation decoder {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ gets its compact binary format (MDQ-P1), a stream decoder that
reconstructs absolute time across counter wraps without allocating, and its first
benchmarks. **Start:** tag `ch01`. **End:** tag `ch02`.
:::

1. Add `minidaq/include/minidaq/format/packed_single.hpp` and
   `minidaq/src/format/packed_single.cpp` as shown in this chapter, plus
   `minidaq/include/minidaq/core/cache.hpp`.
2. Add `minidaq/tests/unit/test_packed_single.cpp`: field independence, round-trip property
   test (100,000 random singles), saturation and NaN handling, unwrapping across 20 wraps,
   the late-word case, invalid crystal counting, little-endian byte decoding.
3. Add the separate `minidaq_alloc_tests` binary with the counting `operator new`.
4. Add Google Benchmark (pinned by commit in `cmake/Dependencies.cmake`) and the
   `benchmarks/` directory with `bm_latency`, `bm_layout`, `bm_alloc`, `bm_false_sharing`
   and `bm_decode`.
5. Record your machine's numbers in your learning log, using the tables in this chapter as
   the template: CPU model, compiler, flags, command line, mean of at least three
   repetitions.

**Definition of done.** `ci/run_all.sh` is green on all three presets; `minidaq_alloc_tests`
passes in the GCC debug and release builds; `bm_decode` decodes more than 100 million words
per second on your machine in a Release build. Tag `ch02`.

## Check yourself {.unnumbered}

1. How many singles fit in one cache line in MiniDAQ's `Single` format, and in MDQ-P1?
2. What is false sharing, and how would you spot it in a profile?
3. A loop over 100 M events takes 200 ms with AoS and 85 ms with SoA. What would you
   expect if the data set were 64 Ki events instead, and why?
4. Why can a `std::pmr::monotonic_buffer_resource` not be used for objects with individual,
   unpredictable lifetimes?
5. Why must a wire format not be defined with C++ bit-fields?
6. The MDQ-P1 time counter wraps every 1.374 s. What goes wrong if a burst of packets
   covering 0.8 s is lost, and how would you detect it?
7. What does a TLB miss cost, and how do huge pages help a DAQ ring buffer?
8. Why does an energy field saturate rather than wrap, and what is the risk of wrapping?
9. A reviewer says "malloc is fast, the arena is premature optimization". What is your
   answer, with numbers from this chapter?
10. Which is faster for summing energies: a vector of 16-byte structs or a vector of floats,
    and does the answer change if every field is used?

## Summary {.unnumbered}

- Cache lines are 64 bytes; latency grows from about 1.7 ns (L1) to about 200 ns (DRAM
  with TLB misses) on the book's machine. Measure yours with `bm_latency`.
- Sequential bytes are cheap, random lines are expensive. Design stages around their
  working set.
- Choose AoS or SoA per pass: read only the bytes you need. Split hot from cold fields.
  Guard struct sizes with `static_assert`.
- Allocate at start-up and recycle in the loop; use pools and `std::pmr` arenas; prove it
  with an allocation-counting test. The gain is predictability more than throughput.
- Define wire and file formats with shifts, masks and explicit little-endian byte order,
  never with bit-fields or `reinterpret_cast`.
- Narrow counters wrap; reconstruct absolute time explicitly and test across many wraps.
- False sharing makes independent counters six times slower in this chapter's benchmark;
  pad per-thread data to its own line.
- Formats and their quantization rules are controlled interfaces with risk relevance.

## Further reading {.unnumbered}

- Ulrich Drepper, "What Every Programmer Should Know About Memory", 2007,
  <https://people.freebsd.org/~lstewart/articles/cpumemory.pdf>. Old hardware, timeless
  principles.
- Richard Fabian, *Data-Oriented Design*, 2018, free online at
  <https://www.dataorienteddesign.com/dodbook/>.
- Mike Acton, "Data-Oriented Design and C++", CppCon 2014 (video on YouTube).
- Denis Bakhvalov, *Performance Analysis and Tuning on Modern CPUs*, 2nd edition, 2024,
  free online at <https://book.easyperf.net/perf_book>. Chapters on the memory hierarchy
  and on measuring cache behavior.
- cppreference: `std::pmr::monotonic_buffer_resource`, `std::bit_cast`,
  `std::hardware_destructive_interference_size`.
- Joe Mario, "C2C - False Sharing Detection in Linux Perf", 2016,
  <https://joemario.github.io/blog/2016/09/01/c2c-blog/>.
