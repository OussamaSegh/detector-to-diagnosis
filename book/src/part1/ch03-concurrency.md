# Concurrency and lock-free pipelines {#ch03}

::: box-why
A data acquisition system (DAQ) is a pipeline: receive, decode, sort, pair, write. At tens of
millions of events per second no single core can do all of it, so each stage runs on its own core
and the stages talk through queues. Fast, low-latency code for a detector stream on more than one
core means three things: queues that cost nanoseconds rather than microseconds per hand-off, a
shutdown that never loses data, and a precise answer to "what happens when the disk is slower than
the detector?". Concurrency bugs are also the hardest bugs to reproduce in the field. A race that
corrupts one batch in a million will not show up in a five-minute test, but it will show up in a
patient scan.
:::

**A day in the life.** A service engineer reports that a long phantom acquisition produced a
list-mode file with 0.3% fewer coincidences than the scanner's hardware counters claim were
sent. No error was logged. You reproduce the run on a test bench and see nothing wrong for an
hour. Then you notice that the writer stage logs a warning about slow disk writes at the same
moment as the gap, and that the decode stage's "dropped" counter is zero. Somewhere between
the network and the disk, batches were thrown away and nobody counted them. The fix takes an
afternoon. Finding it took a week, because the pipeline did not keep accounts. This chapter
builds a pipeline in which every item that enters is either delivered or counted, at every
stage, and in which TSan, the ThreadSanitizer, checks the hand-offs on every CI run.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Explain the C++ memory model (happens-before, acquire/release, sequential consistency)
   well enough to review lock-free code and say why a given memory order is sufficient.
2. Implement and test a single-producer single-consumer (SPSC) ring buffer, and measure it
   honestly.
3. Choose between mutexes, condition variables, atomics and lock-free queues for a given
   pipeline stage, and justify the choice with numbers.
4. Design a pipeline with bounded queues, batching, back-pressure and an explicit drop
   policy, with counters that account for every item.
5. Detect data races with ThreadSanitizer, write stress tests that make races likely, and
   know the limits of both.

## Prerequisites and estimated time {.unnumbered}

Chapters 1 and 2: strong types, `Single`, the MDQ-P1 format and its decoder, cache lines and
false sharing. You should have written a program with `std::thread` before. You do not need
prior experience with atomics. Reading: about 3.5 hours. Exercises: 10 to 14 hours, of which
Exercise 3.3 alone takes 4 to 6. Milestone: 3 hours. In the 10-week schedule at the front of the
book, this chapter is in week 2, with Chapters 9 and 13.

## Threads, std::jthread and stop tokens

### The intuition

A thread is an independent sequence of execution inside your process. All threads share the
same memory. That is what makes them cheap to communicate between, and it is also what makes
them dangerous. A DAQ uses a small, fixed number of long-lived threads, one per pipeline
stage, created at start-up and stopped at the end of an acquisition. It does not create a
thread per packet or per batch. Thread creation costs tens of microseconds and involves the
kernel, which is exactly what the hot path must avoid (Chapter 4).

### std::jthread: a thread that cleans up after itself

C++11's `std::thread` has a trap: if a `std::thread` object is destroyed while still
joinable, the program calls `std::terminate`. Every early return or exception between
starting a thread and joining it is a crash. C++20's [`std::jthread`]{.idx key="jthread"}
fixes this the RAII way. Its destructor requests a stop and then joins. It also carries a
[stop token]{.idx key="stop token"}: a cooperative cancellation flag that the thread
function can receive as its first parameter and poll, or wait on.

MiniDAQ's pipeline starts its five stages like this:

```{.cpp include="minidaq/src/pipeline/acquisition_pipeline.cpp" from="void AcquisitionPipeline::start()" to="=}"}
```

Notice two design choices. First, consumers start before producers, so the source never
fills a queue that nobody reads. Second, only the source receives a stop token. Stopping a
pipeline means stopping the *input*. Every later stage keeps running until its input is
closed and drained, so a stop never discards data that was already accepted. The other
threads end because their input ends, not because someone tells them to.

### Waiting without polling: condition_variable_any and stop tokens

A stage that waits for work can spin (fast to wake, burns a core), sleep in a loop (wastes
latency) or block on a [condition variable]{.idx}. A blocked thread costs nothing until
someone notifies it. The classic bug is a thread blocked in `std::condition_variable::wait`
that never wakes up when you want to stop it, because nobody notifies it. C++20 added an
overload to `std::condition_variable_any` that waits on a predicate *and* a stop token, and
returns when either the predicate is true or a stop was requested. Exercise 3.6 builds a
worker on it:

```{.cpp include="exercises/ch03/e6_stop_token/solution/worker.hpp" from="void run(std::stop_token st) {" to="=}"}
```

When the wait returns, an empty queue means "stopped and drained". Anything else is work.
The handler runs without the lock held. Calling unknown code while holding a lock invites
deadlock, and it blocks producers for as long as the handler runs.

MiniDAQ's hot-path stages do not use condition variables. A notify costs a system call
when a thread is actually waiting. At 10,000 batches per second that is acceptable, at
10 million items per second it is not. Instead they use the `Backoff` policy below: spin
briefly, then yield, then sleep for short intervals. Condition variables are the right tool
for the control plane, where the work is commands, configuration and state changes.

```{.cpp include="minidaq/include/minidaq/pipeline/backoff.hpp" from="class Backoff {" to="=};"}
```

The `PAUSE` instruction tells an x86 core that it is in a spin loop, which saves power and
frees resources for the other hyper-thread. The policy is configurable because the right
answer depends on the machine. On an isolated core under the real-time profile of Chapter
4, you spin only. On a shared CI runner, sleeping keeps idle stages from starving the busy
ones.

### Thread pools: right for reconstruction, wrong for acquisition

A [thread pool]{.idx} runs many short tasks on a fixed set of worker threads. It fits
throughput-oriented work with independent tasks: reconstructing image slices, computing
normalization factors, running Monte Carlo batches. It fits a DAQ pipeline badly, for three
reasons. Ordering matters: batch 1001 must be paired after batch 1000. Each stage's latency
must be bounded, so it must not queue behind unrelated tasks. And each stage has state, such
as the time unwrapper, the carried single or the open file, that belongs to one thread.
Dedicated, pinned threads per stage give you all three. If a stage is too slow for one core,
you split it by data (for example, decode boards 0 to 11 on one thread and 12 to 23 on
another) and merge downstream (Chapter 9), rather than handing its work to a pool.

::: box-mistakes
- **Detached threads.** A detached thread cannot be joined, so you cannot know when it has
  finished touching shared objects. In a DAQ every thread is joined before the objects it
  uses are destroyed. `std::jthread` makes this the default.
- **Stopping every stage at once.** If you request a stop on all threads together, a
  downstream stage may exit while upstream batches are still in flight, and those batches
  are lost without a count. Stop the source, then let each stage drain and close its output.
- **Notifying under the lock, or forgetting to notify.** Notifying while holding the lock is
  legal but wakes a thread that immediately blocks on the mutex. Forgetting to notify after a
  state change makes the waiter hang. Change the state under the lock, release it, then
  notify.
- **Member order with a thread member.** If a `std::jthread` member is declared before the
  members its thread function uses, the thread can start before they are constructed and
  still run after they are destroyed. Declare the thread member last.
:::

## The memory model: atomics, orders and happens-before

### The intuition

On a single thread, your program behaves as if every statement runs in order. With several
threads that illusion breaks. Compilers reorder memory accesses, and CPUs execute them out
of order and buffer stores. Each core sees memory through its own caches. The [C++ memory
model]{.idx key="memory model"} is the contract that tells you which reorderings you can
observe and how to forbid the ones you cannot tolerate.

The most important rule is short. **A [data race]{.idx} is undefined behavior.** A data race
is two accesses to the same memory location from different threads, at least one of them a
write, that are not ordered by happens-before and are not both atomic. Undefined behavior
here is not a theoretical concern. The compiler assumes there are no races and optimizes
accordingly. It may keep a variable in a register forever, or read a struct as one 8-byte
word in one build and as two 4-byte words in another. Section 3.5 shows a tool missing a
race for exactly this kind of reason.

### Happens-before, in one picture

[Happens-before]{.idx} is the ordering relation that the model guarantees. Within one thread,
statements are ordered by program order ("sequenced-before"). Between threads, the main way
to create order is a **release** operation in one thread that is observed by an **acquire**
operation in another. If thread P writes data and then stores a flag with
`memory_order_release`, and thread C loads that flag with `memory_order_acquire` and sees the
stored value, then everything P wrote before the store happens-before everything C does after
the load. That is the [message-passing]{.idx key="message passing"} pattern, and every queue
in this chapter is built on it.

```{.dot caption="Message passing with release and acquire. The release store and the acquire load that reads its value synchronize. Program order inside each thread plus that synchronization edge make the write of the payload happen before its read." width="50%"}
digraph mp {
  rankdir=TB; nodesep=0.5; ranksep=0.35;
  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, fillcolor="#eef3fb", color="#4a6fa5"];
  edge [fontname="Helvetica", fontsize=10];
  subgraph cluster_p { label="producer thread"; labeljust=l; margin=18; fontname="Helvetica"; color="#999999";
    p1 [label="payload = 42\n(plain write)"];
    p2 [label="ready.store(true,\n  release)", fillcolor="#dff0d8", color="#3c763d"];
    p1 -> p2 [label=" sequenced-before"];
  }
  subgraph cluster_c { label="consumer thread"; labeljust=l; labelloc=b; margin=18; fontname="Helvetica"; color="#999999";
    c1 [label="ready.load(acquire)\n== true", fillcolor="#dff0d8", color="#3c763d"];
    c2 [label="read payload\n(sees 42)"];
    c1 -> c2 [label=" sequenced-before"];
  }
  p2 -> c1 [label=" synchronizes-with", color="#3c763d", fontcolor="#3c763d", penwidth=2];
}
```

MiniDAQ's tests include this pattern as a stress test:

```{.cpp include="minidaq/tests/unit/test_memory_model.cpp" snippet="mp"}
```

### The memory orders you will actually use

| Order | What it guarantees | Where MiniDAQ uses it |
|---|---|---|
| `relaxed` | The operation is atomic (no torn values, no lost increments). No ordering with other memory. | Statistics counters; reading your *own* index in a ring |
| `acquire` (loads) | Later reads and writes in this thread cannot move before it. Pairs with a release. | Reading the other side's index in a ring |
| `release` (stores) | Earlier reads and writes in this thread cannot move after it. Pairs with an acquire. | Publishing a slot or a batch |
| `acq_rel` (read-modify-write) | Both of the above | Not needed in this chapter |
| `seq_cst` (default) | Acquire/release plus a single total order of all seq_cst operations, agreed on by every thread | Simple flags where cost does not matter |

The default for every `std::atomic` operation is `seq_cst`. It is the easiest to reason about
and, on x86, the most expensive for stores. On x86, GCC and Clang compile an acquire load and
a release store to plain `MOV` instructions, because the x86 memory model already provides
those guarantees for ordinary loads and stores. A `seq_cst` store becomes an `XCHG` (or a
`MOV` followed by `MFENCE`), which waits for the core's store buffer to drain. On AArch64,
acquire and release map to the dedicated `LDAR` and `STLR` instructions. You can check all of
this in Compiler Explorer (Chapter 5).

### What seq_cst buys: store buffering, measured

What exactly does `seq_cst` forbid that acquire/release allows? The classic example is
[store buffering]{.idx key="store buffering"}. Two threads each store to one variable and then
load the other. Under `seq_cst` at least one thread must see the other's store. Under
acquire/release both can read the old value, because nothing orders a store before a *later
load of a different variable*. This is not a theoretical loophole. A core's store sits in its
store buffer for a few nanoseconds, and the load that follows can complete first.

```{.cpp include="minidaq/tests/unit/test_memory_model.cpp" snippet="sb"}
```

On the book's machine (4 vCPU Intel Xeon VM at 2.30 GHz, GCC 13.3, -O2), five runs of one
million trials each gave 2, 7, 4, 11 and 5 "both read zero" outcomes with acquire/release, and
0 every time with `seq_cst`. The rate is tiny, because the trial harness lets one thread run
ahead most of the time, but it is not zero. A one-in-200,000 event in a DAQ happens many
times per second.

Why does an SPSC queue not need `seq_cst`, then? Because it never relies on store-then-load
ordering across *different* variables in the same thread. The producer writes a slot, then
releases `tail`. The consumer acquires `tail`, then reads the slot. Each decision ("is there
data?", "is there space?") depends on one index written by one thread. Message passing is
exactly the guarantee acquire/release gives. Store buffering would only matter if, for
example, the producer stored `tail` and then decided something from a load of `head` that had
to be ordered after its own store. Our ring never does that. Lock-free algorithms that do, such
as Dekker-style mutual exclusion or some hazard-pointer schemes, need `seq_cst` or explicit
fences.

### Fences, briefly

`std::atomic_thread_fence(order)` imposes ordering without an atomic variable of its own. A
release fence followed by a relaxed store behaves, for synchronization purposes, like a
release store, and similarly for acquire. Fences are useful when one synchronization covers
many relaxed operations, or when porting algorithms from papers that are written with fences.
MiniDAQ does not use standalone fences. Operations with an explicit order on the variable that
carries the information are easier to review, and reviewability is a safety property.

### The ABA problem

The [ABA problem]{.idx key="ABA problem"} affects lock-free structures that use
compare-and-swap (CAS) on pointers. A thread reads pointer value A, gets preempted, and in the
meantime other threads pop A, push B, free A and push a new node that happens to be allocated
at the same address A. The first thread's CAS sees A, concludes nothing changed, and succeeds
on a structure whose meaning has changed completely. The usual defenses are tagged pointers (a
version counter next to the pointer), hazard pointers, epoch-based reclamation, or not freeing
memory at all. MiniDAQ's queues avoid the problem by design. The SPSC ring uses
monotonically increasing 64-bit indices that never repeat in practice (at a billion operations
per second, 2^64 takes about 584 years), and the multi-producer queue below uses per-slot
sequence numbers. Neither ever frees memory while running.

::: box-mistakes
- **"It's atomic, so it's safe."** Atomicity of each operation does not make a sequence of
  operations atomic. `if (q.size() > 0) q.pop()` on two threads is a race even if both calls
  are atomic.
- **Relaxed flags that publish data.** A `relaxed` store of a "ready" flag publishes nothing:
  the reader can see the flag and stale data. Exercise 3.2 seeds exactly this bug.
- **`volatile` for threads.** `volatile` prevents some compiler optimizations but provides no
  atomicity and no ordering between threads. It is for memory-mapped hardware registers, not
  synchronization.
- **Reasoning from x86.** Code with a missing acquire often works on x86 and fails on ARM,
  or works at -O0 and fails at -O2. If you cannot point to the release/acquire pair that
  orders an access, the code is wrong, whatever the tests say.
:::

## Ring buffers: SPSC, MPMC and batching

### The intuition

A [ring buffer]{.idx} is an array used as a circular queue. The producer writes at `tail` and
advances it, and the consumer reads at `head` and advances it. When each index has exactly
one writer, the producer and the consumer never write the same variable. That is what makes
the single-producer single-consumer case so cheap: no locks, no compare-and-swap, just loads
and stores with the right orders. The idea goes back to Leslie Lamport's 1983 proof that such
a queue is correct without locks. MiniDAQ's version follows the design popularized by Erik
Rigtorp's `SPSCQueue`.

```{.dot caption="An SPSC ring of capacity 8 holding three items (indices 10, 11 and 12 in slots 2, 3 and 4). Indices grow without bound and are masked with capacity - 1 to find the slot, so tail - head is the fill level and the ring can use all eight slots. The producer owns tail, the consumer owns head, and each keeps a cached copy of the other's index on its own cache line." width="85%"}
digraph ring {
  rankdir=TB; nodesep=0.4; ranksep=0.5;
  node [fontname="Helvetica", fontsize=11];
  edge [fontname="Helvetica", fontsize=10];
  slots [shape=record, style=filled, fillcolor="#f7f7f7",
         label="<s0> 0|<s1> 1|<s2> 2\ndata|<s3> 3\ndata|<s4> 4\ndata|<s5> 5\nfree|<s6> 6|<s7> 7"];
  cons [shape=box, style="rounded,filled", fillcolor="#fcf8e3", color="#8a6d3b",
        label="consumer cache line\nhead = 10 (atomic)\ncached_tail"];
  prod [shape=box, style="rounded,filled", fillcolor="#dff0d8", color="#3c763d",
        label="producer cache line\ntail = 13 (atomic)\ncached_head"];
  cons -> slots:s2:n [label="reads next: 10 & 7 = 2"];
  slots:s5:s -> prod [dir=back, label="writes next: 13 & 7 = 5"];
}
```

### Design choices, one at a time

**Power-of-two capacity.** If the capacity is a power of two, `index & (capacity - 1)` is the
slot number, which is cheaper than `%`. And because the indices themselves grow without bound
and wrap modulo 2^64 (well-defined for unsigned integers), `tail - head` is always the number
of items in the ring. You can use every slot and still tell "full" from "empty". The
alternative, wrapping the indices at the capacity, needs one wasted slot or an extra flag.

**Separate cache lines.** `head` is written by the consumer and `tail` by the producer. If
they shared a cache line, every update would steal the line from the other core: the false
sharing of Chapter 2.

```{.cpp include="minidaq/include/minidaq/pipeline/spsc_ring.hpp" snippet="layout"}
```

**Cached indices.** To know whether there is space, the producer must read `head`, a line the
consumer keeps writing, so every read can be a cache miss. Instead the producer keeps a
private copy of `head` and re-reads the shared one only when the copy says the ring is full.
The consumer does the same with `tail`. When the ring is neither nearly full nor nearly empty,
most operations touch only lines their own core owns.

**Memory orders.** Each side reads its own index `relaxed` (nobody else writes it), reads
the other side's index with `acquire`, and publishes its own with `release`:

```{.cpp include="minidaq/include/minidaq/pipeline/spsc_ring.hpp" snippet="push"}
```

```{.cpp include="minidaq/include/minidaq/pipeline/spsc_ring.hpp" snippet="pop"}
```

Read the pairs. The producer's release store of `tail + 1` publishes the slot it just wrote,
and the consumer's acquire load of `tail` makes the slot's contents visible before it reads
them. In the other direction, the consumer's release store of `head + 1` says "I have
finished reading this slot", and the producer's acquire load of `head` guarantees that read
is complete before the slot is overwritten. Without that second pair, the producer could
overwrite a slot that the consumer is still reading.

### Measured: what each choice is worth

The benchmark `bm_spsc` moves 4 Mi (4,194,304) 64-bit values from a producer thread to a
consumer thread per iteration, with the threads pinned to CPUs 0 and 1. Each variant isolates
one design decision. `NaiveRing` and `AcqRelRing` are the same ring without cached indices,
with `seq_cst` and with acquire/release respectively:

```{.cpp include="benchmarks/bm_spsc.cpp" snippet="naive"}
```

Measured on the book's machine (4 vCPU Intel Xeon VM at 2.30 GHz, GCC 13.3, -O2,
`bm_spsc --benchmark_repetitions=10`), in millions of items per second:

| Variant | min | median | max |
|---|---|---|---|
| `std::mutex` + `std::deque` | 4.9 | 5.2 | 5.6 |
| Ring, `seq_cst`, no cached indices | 5.5 | 7.1 | 7.6 |
| Ring, acquire/release, no cached indices | 36.4 | 61.7 | 140.4 |
| `minidaq::SpscRing` (acquire/release, cached indices) | 39.8 | 51.6 | 63.7 |
| `minidaq::MpmcQueue`, used with one producer and one consumer | 25.7 | 28.7 | 35.0 |
| `SpscRing`, batches of 16 | 142.3 | 159.0 | 227.6 |
| `SpscRing`, batches of 256 | 363.7 | 386.8 | 462.7 |

Three conclusions are robust. Every run showed them and the gaps are far larger than the
noise:

1. **The memory order is worth almost an order of magnitude.** The `seq_cst` ring is barely
   faster than a mutex. Every store waits for the store buffer to drain, and that cost is paid
   twice per item.
2. **Batching is the biggest lever of all.** Moving 256 items per index update gives seven
   times the per-item rate. The cost of a hand-off is per synchronization, not per byte, so
   you pay it once per batch. This is why MiniDAQ's pipeline passes batches, not singles.
3. **Generality costs.** The multi-producer queue pays for a compare-and-swap on every
   operation even when there is only one producer.

One question is **not** answered by this machine: the value of cached indices. The uncached
acquire/release ring varied from 36 to 140 M/s between runs, while the cached ring stayed
between 40 and 64 M/s. In a heap-allocated rerun, the cached ring once reached 363 M/s. Per-item
hand-off between two threads in lockstep is extremely sensitive to the hypervisor's scheduling
and to whether the ring happens to settle nearly empty, nearly full or in between. Only in the
last case do cached indices save anything. verify: repeat this comparison on bare metal with
isolated cores (Chapter 4) before drawing conclusions about cached indices. Rigtorp's
`SPSCQueue` documentation presents them as its key optimization (verify: its benchmark
section and hardware). The honest summary for this book is the one Chapter 5 will make a
rule: a result that changes by 4x between repetitions is not a result, and you report the
spread along with the median.

Exercise 3.1 asks for 50 M singles per second between two pinned threads. With 16-byte
`Single` values, the reference solution's per-item median was 33 M/s on this VM and batches of
64 reached 314 M/s, so batching meets the target with a large margin.

### Multiple producers: Vyukov's bounded queue

Sometimes several threads must feed one queue. Chapter 9 has one receiver thread per group of
front-end boards, all feeding a merger. With two producers, the "one writer per index" property
is gone, and the producers must agree on who gets which slot. MiniDAQ uses Dmitry Vyukov's
[bounded MPMC queue]{.idx key="MPMC queue"} (multi-producer multi-consumer). Each slot carries
a sequence number that says whose turn it is. A producer claims a position with a CAS on the
shared `enqueue_pos_`, writes the value, then releases the slot by storing `pos + 1` into its
sequence:

```{.cpp include="minidaq/include/minidaq/pipeline/mpmc_queue.hpp" snippet="push"}
```

It is lock-free in the everyday sense, but it is not wait-free. A producer that is preempted
between winning the CAS and publishing the slot blocks the consumer of that slot until it runs
again. On a real-time-configured machine with pinned threads that is rare. On an overloaded
one it is a latency spike, and Chapter 4's histograms will show it. An MPSC queue
(multi-producer single-consumer) is this queue used with one consumer. A dedicated MPSC design can save the consumer's CAS, but
the measured cost above (29 M/s against 52 M/s for SPSC, both single-item) tells you to keep
multi-producer queues off the hottest path whenever you can restructure as several SPSC
queues.

### When to use what

| Situation | Use | Why |
|---|---|---|
| Stage to stage, one thread each side, high rate | SPSC ring of batches | Cheapest correct hand-off |
| Several producers, one consumer, moderate rate | MPMC (or MPSC) queue of batches | Avoids a lock, keeps order per producer |
| Commands, configuration, state changes | `std::mutex` + `std::condition_variable_any` | Rare, needs blocking waits; simplest correct code |
| Counters read by a monitor | `std::atomic` with `relaxed` | Atomicity without ordering |
| Large configuration read by hot threads | Immutable object published through an atomic pointer, or a mutex | Readers never see a half-written object |

::: box-mistakes
- **Calling a ring from the wrong side.** While reviewing this chapter's own code, we found a
  `Channel::release_unused()` that pushed a batch back onto the ring of empty batches *from the
  producer side*. That ring's only writer is supposed to be the consumer, so the push made it a
  two-producer ring. No test failed, because the path was rare. The fix keeps the spare batch in
  a producer-local slot. Write down which thread may call each function, in the header, and
  check every call site against it.
- **Non-power-of-two capacity with masking.** `index & (capacity - 1)` is only correct for
  powers of two. Round up in the constructor, as `std::bit_ceil` does.
- **Benchmarking per-item hand-off and calling it throughput.** A pipeline moves batches. Measure
  the hand-off you will actually use.
:::

## Pipeline design: batches, back-pressure and drop accounting

### The intuition

A pipeline is a chain of stages connected by bounded queues. Its throughput is the throughput of
its slowest stage. Its latency is the sum of the stage latencies plus the time items spend
waiting in queues. Bounded queues are essential: an unbounded queue in front of a slow stage
grows until the machine runs out of memory, which turns a slowdown into a crash. When a bounded
queue is full, something has to give, and the design question is what.

```{.dot caption="MiniDAQ's acquisition pipeline in Chapter 3. Five threads, four channels. Each channel is a pool of pre-allocated batches that circulate between two SPSC rings: full batches flow downstream, empty ones flow back. Only the source may drop data, and only under the drop policy; every stage counts what it receives, emits, drops and filters." width="45%"}
digraph pipeline {
  rankdir=TB; nodesep=0.3; ranksep=0.3;
  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, fillcolor="#eef3fb", color="#4a6fa5"];
  edge [fontname="Helvetica", fontsize=9];
  hw [label="front-end\nboards", shape=box3d, fillcolor="#f7f7f7", color="#777777"];
  src [label="source\n(block | drop)"];
  dec [label="decode\nMDQ-P1"];
  srt [label="sort\n(per batch)"];
  par [label="pair\n(window)"];
  wri [label="write\n(sink)"];
  disk [label="list-mode\nfile", shape=cylinder, fillcolor="#f7f7f7", color="#777777"];
  hw -> src [label="words"];
  src -> dec [label="Channel<uint64_t>"];
  dec -> srt [label="Channel<Single>"];
  srt -> par [label="Channel<Single>"];
  par -> wri [label="Channel<Coincidence>"];
  wri -> disk;
}
```

### Batches and channels

MiniDAQ's `Channel<T>` connects exactly one producer stage to one consumer stage. It owns a
fixed pool of `Batch<T>` objects, each a pre-sized vector plus a size and a sequence number. Two
SPSC rings carry *pointers* to batches: full ones forward, empty ones back. The producer acquires
an empty batch, fills it and publishes it. The consumer receives it, processes it and releases
it. After construction, no memory is allocated (Chapter 2's rule), and "the pipeline is full"
shows up in exactly one place: the producer finds no empty batch.

```{.cpp include="minidaq/include/minidaq/pipeline/channel.hpp" from="// Producer side." to="queued_approx"}
```

The `closed()` comment states a subtle but essential rule. The producer publishes its last batch
and then closes the channel. A consumer that sees `receive()` return nothing and then sees
`closed()` must call `receive()` once more. The batch may have been published between its two
checks. Because `close()` is a release store and `closed()` an acquire load, seeing the closed
flag guarantees that every batch published before it is visible. The library test
`ChannelStress.CloseAfterLastPublishIsNeverMissed` runs that race 200 times.

How big should a batch be? Bigger batches amortize the hand-off cost and the per-batch work,
smaller ones reduce latency and cache footprint. At 10 M singles/s, a batch of 4,096 singles
holds about 0.4 ms of data, and 64 such batches per channel hold about 26 ms. That is
comfortable for disk hiccups and negligible for a display that updates every second. The
measurement below shows the per-stage cost matters as much as the hand-off.

### Back-pressure or drop: the policy is a requirement

When the source finds no empty batch, it has two choices. With **back-pressure** it waits,
and the delay propagates upstream: to the network stack, to the switch buffers, and finally
to the front-end boards' FIFOs. With a flow-controlled link (TCP, or a custom protocol with
credits), that is lossless until the hardware buffers overflow. With **drop**, the source still
reads the data from the hardware, so the boards are never stalled, but it throws the batch away
and counts every word.

```{.cpp include="minidaq/src/pipeline/acquisition_pipeline.cpp" snippet="source"}
```

Neither policy is "correct" in the abstract. Which one your scanner needs depends on what the
front-end does when it is not drained. assumption: confirm with team whether the boards
have flow control, how deep their buffers are, and whether losing a burst or stalling the
detector is the lesser harm. What *is* non-negotiable is that a loss is counted where it
happens and reported. Dead-time and randoms corrections in quantitative PET assume that you
know how much data was lost (Chapter 11). Exercise 3.5 implements three policies (reject, drop newest,
drop oldest) with exact accounting and discusses why only the entry stage may drop at all.

**Stages inside the PC always block.** If the writer falls behind, the pair stage waits for an
empty batch, then the sort stage waits, and so on back to the source, where the policy decides.
That is the answer to this chapter's second check-yourself question. When the writer falls
behind, the DAQ must apply back-pressure up to a single, deliberate decision point, never
drop silently in the middle, and raise an alarm when the drop counter moves.

### Keeping accounts

Every stage owns a `StageStats` on its own cache line. A single writer means relaxed atomic
increments are enough, and the control API reads them without stopping the pipeline (Chapter
6). Two counters are easy to confuse and must be kept apart:

- `items_dropped`: data lost because the system was too slow. Only the source, only under the
  drop policy.
- `items_filtered`: data removed *by design*. Invalid words rejected by the decoder, singles that
  found no coincidence partner.

The test `Pipeline.MatchesSingleThreadedReference` checks the books at every boundary. Source
`in == out + dropped`. Decode `in == out + dropped + filtered`. Sort `in == out`. Pair
`in == 2 * out + filtered`, since two singles make one coincidence. Write receives exactly what
pair emitted. A first draft of Exercise 3.3 in this book stated `in == out + dropped` for every
stage, and the reference solution failed it at once: the pair stage turns 300,000 singles into
about 73,000 coincidences. A test written as an equation finds a wrong specification as quickly
as a wrong implementation.

```{.cpp include="minidaq/src/pipeline/acquisition_pipeline.cpp" snippet="decode"}
```

### Determinism: sort by a total order

The Chapter 3 sort stage is deliberately simple. It sorts each batch by time, and Chapter 10
replaces it with a proper merge. Even this simple version taught a lesson during review. The
first version sorted by time only, and the pipeline test that compares the threaded output with
a single-threaded reference failed on coincidence number 998. MDQ-P1 time has 5 ps resolution,
so at 10 M singles/s two singles share a timestamp now and then, and `std::sort` is not stable.
Equal elements come out in an unspecified order, which here meant a different pairing. The fix
is a total order:

```{.cpp include="minidaq/include/minidaq/pipeline/acquisition_pipeline.hpp" snippet="order"}
```

Reproducibility is not a nicety. If two runs over the same input give different output, a
regression test cannot tell a bug from noise, and you cannot reproduce a field problem from a
recorded raw file. (This fix left a gap that no unit test could see: two singles with one time
that fall into two batches. A system test found it much later; Chapter 19 tells that story.)

### Measured: the pipeline runs at the speed of its slowest stage

`bm_pipeline` pushes 8 Mi pre-generated MDQ-P1 words through the five-stage pipeline (book's
machine, GCC 13.3, -O2, five threads on four vCPUs, five repetitions), in millions of words per
second:

| Batch size | Batches per channel | min | median | max |
|---|---|---|---|---|
| 64 | 64 | 40.1 | 42.6 | 43.6 |
| 512 | 64 | 45.5 | 47.3 | 48.3 |
| 4,096 | 64 | 32.6 | 33.1 | 33.7 |
| 4,096 | 8 | (one run) | 34.4 | |

Why is the largest batch slowest? The first hypothesis was cache footprint. 64 batches of
4,096 singles is 4 MiB per channel, far beyond the 2 MiB L2. But shrinking the channel to 8
batches barely helped, so that hypothesis is wrong. Timing the stages separately finds the
real cause. Decoding runs at 230 to 260 M words/s in this setup (one run per batch size, at
this chapter's tag; Chapter 5's dedicated benchmark measures 330) and is not the problem.
Sorting each batch on its own runs at about 90 M singles/s for batches of 64, 42 to 50 for
512, and 35 to 37 for 4,096. Sorting is O(n log n), so its cost *per single* grows with the batch size, and at 4,096
the sort stage alone runs at the speed of the whole pipeline. At 64, sorting is cheap and the
per-batch hand-off and scheduling overhead of five threads on four cores dominates. Exercise
3.3 has you add busy-time accounting so the pipeline reports its own bottleneck. Chapter 5
does the same with a profiler, and finds that the sort was also more than three times slower than it
had to be.

Even the slowest configuration handles 33 M words/s. That is more than three times the 10 M
singles/s this book uses as its working rate (assumption: confirm with team), but only just
above the 30 M singles/s of Chapter 2's high-activity estimate: no margin at all. On the real
acquisition PC, with pinned cores and without a hypervisor, expect better numbers. Measure
them.

::: box-mistakes
- **Unbounded queues.** A `std::queue` between stages "never blocks". It grows during every
  disk hiccup and, eventually, takes the machine down. Every queue has a capacity and every
  capacity has a reason.
- **Dropping in the middle.** A drop inside the PC is invisible to the hardware counters and
  breaks dead-time accounting. Drop at the entry or not at all.
- **Counting at the wrong place.** Count a drop where the decision is taken, in the same
  statement. A counter updated "later" is a counter that misses the early-exit path.
- **One counter for two meanings.** Keep "lost because slow" apart from "removed by design".
:::

## Testing concurrent code: TSan, stress tests, latches and barriers

### The intuition

A concurrency bug is a property of an interleaving, and the number of interleavings is
astronomical. A test that passes tells you that the interleavings it happened to run were
fine. You improve the odds in two ways. *Stress tests* make bad interleavings likely: small
queues, many iterations, payloads that reveal loss and reordering. *Race detectors* such as
ThreadSanitizer turn a race that happened to be harmless in this run into a report. Neither
proves the absence of bugs. Together with code whose synchronization you can point to, they
are the best evidence you can produce.

### ThreadSanitizer

[ThreadSanitizer]{.idx key="ThreadSanitizer (TSan)"} (TSan), built into GCC and Clang with
`-fsanitize=thread`, instruments every memory access and every synchronization operation.
It keeps a vector clock per thread, which records what each thread has "heard about" every
other thread through acquire/release, mutexes, thread creation and joins. For recent accesses
to each 8-byte word it keeps a small history in shadow memory. When two accesses from different
threads conflict and neither is ordered before the other, it prints both stacks and the
places where the threads were created. The Clang documentation quotes a typical slowdown of 5x
to 15x and a memory overhead of 5x to 10x. That is too slow for production and fine for CI.
TSan cannot be combined with AddressSanitizer in the same build, which is why MiniDAQ has
separate `asan-ubsan` and `tsan` presets and CI runs both.

Exercise 3.2 seeds two races. Here is TSan's report for the first one, two decoder threads
incrementing the same histogram bin (abridged; the full report is in the solution's
`REPORT.md`):

```text
WARNING: ThreadSanitizer: data race
  Write of size 8 at 0x7ffec91e6618 by thread T2:
    #0 ex::EnergyMonitor::record(float) .../starter/monitor.hpp:24:48
  Previous write of size 8 at 0x7ffec91e6618 by thread T1:
    #0 ex::EnergyMonitor::record(float) .../starter/monitor.hpp:24:48
  Location is stack of main thread.
```

Read a report from the top. The two accesses, the variable (the location line), then the
thread creation stacks that tell you *which* threads. The fix is almost never "add a mutex
around this line". Ask which thread should own the data, and what ordering the readers need.

### What TSan missed, and why the preset builds at -O0

The second seeded race publishes a configuration through a relaxed flag. Under the `tsan`
preset as originally configured, which built at -O2 like most sanitizer setups, TSan **never
reported it**. The test even observed a torn window (a new `low` with an old `high`) in one of
ten runs, so the race was real and happening. Investigation showed the following, with Clang 18:

| Monitor object | -O0 | -O1 | -O2 | -O3 |
|---|---|---|---|---|
| on the stack of the test | reported 3/3 | 0/6 | 0/6 | 0/6 |
| on the heap | reported 4/4 | not measured | reported 4/4 | not measured |
| static | not measured | not measured | reported 4/4 | not measured |

In the optimized builds the reader's two `float` loads from the stack object were not
instrumented at all (visible in the LLVM IR: no `__tsan_read` call before them), although the
object's address had been handed to the other thread through a lambda capture. verify: the
exact cause inside LLVM's TSan instrumentation pass, which skips some accesses to stack
objects it considers thread-local. The consequences for MiniDAQ are concrete. The `tsan`
preset now builds at -O0, the exercise test keeps the shared object on the heap, and the lesson
goes into the review checklist: **a clean TSan run is evidence, not proof**. TSan also cannot
see races in code that does not run, and it says nothing about atomicity violations built from
individually atomic operations, such as check-then-act on two atomics.

### Stress tests that find bugs

A good concurrent stress test has five properties. You can check each one in
`minidaq/tests/unit/`:

1. **Small capacities.** A ring of 1,024 slots fills and empties constantly. A channel of 2 to 8
   batches makes "full" and "closed" happen often.
2. **Payloads that encode their identity.** Sequence numbers (and a second field derived from
   them, such as `~i`) reveal lost, duplicated, reordered and torn items.
3. **A reference.** `Pipeline.MatchesSingleThreadedReference` computes the expected
   coincidences with a plain loop over the same words and compares element by element.
4. **Repetition of the dangerous moment.** The close/drain race happens once per run, so the
   test runs it 200 times:

   ```{.cpp include="minidaq/tests/unit/test_channel.cpp" from="TEST(ChannelStress, CloseAfterLastPublishIsNeverMissed)" to="=}"}
   ```

5. **A deadline.** A broken queue makes a stress test spin forever, and a hung CI job tells you
   nothing. The first version of Exercise 3.1's tests did exactly that against the unfinished
   starter. The tests now give up after 30 seconds and release the producer thread through a
   scope guard, so the failure is a clear message and not a timeout.

### std::latch and std::barrier

Two C++20 primitives make test harnesses and phased algorithms simpler. A
[`std::latch`]{.idx key="latch"} is a single-use countdown: threads `arrive_and_wait()` and
nobody proceeds until the count reaches zero. That is the right tool for "start all stages at
the same moment" in a benchmark or a stress test. A [`std::barrier`]{.idx key="barrier"} is
reusable and runs a completion function once per phase, after every participant has arrived and
before any is released. Iterative calibrations that alternate "every worker computes" and "one
step merges" map onto it directly. Because the barrier orders every worker's writes before the
completion function, and the completion function's writes before the next phase, the
completion function can read and reset per-worker partial results without atomics:

```{.cpp include="exercises/ch03/e4_latch_barrier/solution/sync.hpp" snippet="barrier"}
```

::: box-mistakes
- **Trusting a green run.** Run stress tests many times (`ctest --repeat until-fail:50`) and
  under TSan, and read the code for the release/acquire pairs anyway.
- **Tests without timeouts.** A hang is the most common symptom of a concurrency bug. Every
  concurrent test needs a deadline, and every thread a way to be released.
- **`sleep_for` as synchronization.** "Wait 10 ms, then the other thread is surely ready" is a
  race with a long fuse. Use a latch.
- **Ignoring TSan reports "because it's only a counter".** A racy counter is undefined behavior
  like any other race, and it hides real reports in the noise. Make it atomic.
:::

::: box-regulated
Concurrency is where software risk analysis and code review meet.

- **Unit acceptance criteria.** For class C software, IEC 62304 asks for additional unit
  acceptance criteria. Among them are proper event sequence, data and control flow, and planned
  resource allocation (clause 5.5.4). The thread ownership rules, queue capacities and the
  drain-on-stop sequence of this chapter are exactly such criteria. Write them down in the
  detailed design, where reviewers can check code against them.
- **Data loss is a hazard input.** Silently dropped batches bias count rates and therefore
  quantitative values. The drop policy and its counters are risk controls, and the tests that
  prove `in == out + dropped + filtered` at every stage are their verification (Chapters 14
  and 15).
- **Tools are part of the evidence.** If you claim "race-free under the tested scenarios",
  record the TSan build configuration with the result. The -O0 finding in this chapter is the
  kind of tool limitation a verification plan should mention.
- **SOUP.** The C++ standard library's threading and atomics are software of unknown provenance
  (SOUP) like any other library you did not develop. Record the toolchain version as part of
  the SOUP list (Chapter 14).
:::

::: box-askteam
1. How many threads does the current acquisition software run, which ones are on the hot path,
   and how do they communicate (locks, queues, shared memory)?
2. What happens today when the writer falls behind? Is there back-pressure to the front-end,
   and do the boards have flow control and how much buffering?
3. Where are data losses counted, and do the counts reach the acquisition log and the
   service tools?
4. Is ThreadSanitizer (or another race detector) run in CI, and on which tests?
5. Has the team ever had a race condition in the field? How was it found and fixed?
:::

## Exercises {.unnumbered}

**Exercise 3.1 (M): An SPSC ring for singles.** *Goal:* implement a lock-free SPSC ring of
`Single` with single and batched push/pop, and reach at least 50 M singles per second between
two pinned threads. *Starter:* `exercises/ch03/e1_spsc_ring/`. *Acceptance:* `tests/test_ring.cpp`
passes in all four presets (FIFO, full/empty, many laps, partial batches, two 2-million-item
stress tests). `bench_ring.cpp` reports at least 50 M/s, with median and spread recorded. *Time:*
2 to 3 hours.

**Exercise 3.2 (M): Catch a seeded race with ThreadSanitizer.** *Goal:* find the two data races
in `EnergyMonitor` with TSan, fix them with the weakest correct synchronization, and write a
report with the TSan excerpts, causes and fixes. *Starter:* `exercises/ch03/e2_seeded_race/`.
*Acceptance:* exact counts from two writer threads, no torn windows, zero TSan reports under the
`tsan` preset, and a `REPORT.md`. *Time:* 90 minutes.

**Exercise 3.3 (H): A four-stage pipeline that reports on itself.** *Goal:* decode, sort, pair
and write on four threads with bounded queues. Each stage reports items in, out, dropped and
filtered, and busy time. *Starter:* `exercises/ch03/e3_four_stage_pipeline/`. *Acceptance:*
output equals a single-threaded reference, conservation holds at every stage, drops are counted
under the drop policy with a slow writer, and the tests are TSan-clean. Then report which stage
limits throughput at batch sizes 64, 512 and 4,096. *Time:* 4 to 6 hours.

**Exercise 3.4 (E, extra): Start together, step together.** *Goal:* use `std::latch` to start
`n` threads at once and `std::barrier` with a completion function to run phased sums.
*Starter:* `exercises/ch03/e4_latch_barrier/`. *Acceptance:* every thread observes all `n`
arrivals (50 repetitions), phase totals are exact, and the completion function runs exactly once
per phase. *Time:* 45 minutes.

**Exercise 3.5 (M, extra): Drop policies you can account for.** *Goal:* implement reject,
drop-newest and drop-oldest with exact accounting, plus loss detection from batch sequence
numbers. *Starter:* `exercises/ch03/e5_drop_policy/`. *Acceptance:* the per-policy tests pass,
the accounting invariants hold over 100,000 random operations, and gaps and reordering are
counted separately. Your notes say which policy belongs where in a DAQ. *Time:* 90 minutes.

**Exercise 3.6 (M, extra): Shut down a waiting worker promptly.** *Goal:* a worker thread that
blocks on `std::condition_variable_any` with its stop token, drains queued items on stop and
refuses new ones. *Starter:* `exercises/ch03/e6_stop_token/`. *Acceptance:* in-order processing,
all queued items handled on stop, an idle worker stops in under 100 ms (a watchdog fails the run
if it hangs), and the tests are TSan-clean. *Time:* 60 minutes.

## MiniDAQ milestone: a threaded acquisition pipeline {.unnumbered}

::: box-milestone
**Goal.** The acquisition core becomes a five-thread pipeline (source, decode, sort, pair,
write) connected by lock-free channels of pre-allocated batches, with per-stage counters that
account for every item, a block or drop policy at the entry, and a drain-on-stop shutdown.
**Start:** tag `ch02`. **End:** tag `ch03`.
:::

1. Add the pipeline headers under `minidaq/include/minidaq/pipeline/`: `spsc_ring.hpp`,
   `mpmc_queue.hpp`, `backoff.hpp`, `channel.hpp`, `stage_stats.hpp` and
   `acquisition_pipeline.hpp`, plus `minidaq/src/pipeline/acquisition_pipeline.cpp`.
2. Add the synthetic source `minidaq/include/minidaq/sim/synthetic_source.hpp` and its `.cpp`.
   It emits a Poisson stream of MDQ-P1 words with about 30% partner singles. This is not physics;
   Chapter 8 replaces it.
3. Link `Threads::Threads` publicly from `minidaq_core`.
4. Add the unit tests `test_spsc_ring.cpp`, `test_mpmc_queue.cpp`, `test_channel.cpp`,
   `test_pipeline.cpp` and `test_memory_model.cpp`, with stress tests sized to finish in seconds
   under TSan.
5. Add the `tsan` preset (Clang, -O0, `-fsanitize=thread`) to `ci/run_all.sh` and to the CI
   matrix.
6. Add `benchmarks/bm_spsc.cpp` and `benchmarks/bm_pipeline.cpp`. Record your machine's numbers
   in your learning log: CPU, compiler, flags, pinning, and median and spread over at least five
   repetitions.

**Definition of done.** `ci/run_all.sh` is green on all four presets (debug, clang-release,
asan-ubsan, tsan). The pipeline tests `MatchesSingleThreadedReference` and
`DropPolicyCountsEveryLostWord` pass 50 times in a row (with `ctest --preset tsan -R Pipeline`
and `--repeat until-fail:50`). `bm_pipeline` moves more than 10 M words/s in a Release build
on your machine. Tag `ch03`.

## Check yourself {.unnumbered}

1. Why does an SPSC queue need only acquire/release and not `seq_cst`?
2. What should a DAQ do when the writer stage falls behind?
3. Define a data race. Why is a data race on a plain `std::uint64_t` counter undefined behavior
   even if "losing a few counts is fine"?
4. In the store-buffering litmus test, both threads read 0 a few times per million trials with
   acquire/release. Which hardware mechanism makes that possible on x86, and why does `seq_cst`
   prevent it?
5. Why does an SPSC ring with monotonically increasing 64-bit indices not suffer from the ABA
   problem?
6. A consumer calls `receive()`, gets nothing, then checks `closed()`, sees `true`, and exits.
   What can go wrong, and what is the fix?
7. Why does MiniDAQ's pipeline give a stop token only to the source thread?
8. Name two reasons why a thread pool is a poor fit for the stages of an acquisition pipeline.
9. The pipeline is slower with batches of 4,096 than with 512. Give the measured explanation,
   and say how you would confirm it on your own machine.
10. A colleague says "TSan is clean, so the code is race-free". Give two reasons from this
    chapter why that does not follow.
11. Why must the sort stage order by (time, crystal) rather than time alone?
12. What is the difference between `items_dropped` and `items_filtered`, and why does it matter
    in a service report?

## Summary {.unnumbered}

- A data race is undefined behavior. Every cross-thread access needs a happens-before edge,
  usually a release store observed by an acquire load.
- SPSC rings need only acquire/release. Store buffering is real (a few per million trials
  here), and it only matters for algorithms that order a store before a load of another
  variable.
- Measured on a VM: a mutex queue moves about 5 M items/s, a `seq_cst` ring about 7, an
  acquire/release ring about 50, and batches of 256 about 390. Hand off batches.
- Per-item benchmarks between two threads are noisy. Report the median and the spread, and
  confirm on bare metal.
- A pipeline runs at the speed of its slowest stage. Here that was the per-batch sort, whose
  cost per single grows with batch size.
- Bound every queue. Apply back-pressure inside the PC and decide drop-or-block at one place,
  the entry.
- Count every item. Check `in == out + dropped + filtered` (and `2 * out` for pairing) at every
  boundary in tests, and keep "lost" apart from "removed by design".
- Stop the source, then drain. Use `std::jthread`, and stop tokens with
  `condition_variable_any` for blocking waits.
- Sort by a total order. Determinism makes regression tests and field reproduction possible.
- Run TSan in CI (MiniDAQ builds it at -O0, after a measured blind spot at -O1 and above), and
  write stress tests with small capacities, identity payloads, references and deadlines.

## Further reading {.unnumbered}

- Anthony Williams, *C++ Concurrency in Action*, 2nd edition, Manning, 2019. The standard
  reference for the memory model, atomics and lock-free design in C++.
- Erik Rigtorp, `SPSCQueue`, <https://github.com/rigtorp/SPSCQueue>. A compact, well-explained
  SPSC ring. Compare it with `spsc_ring.hpp`.
- Jeff Preshing, "Acquire and Release Semantics", 2012,
  <https://preshing.com/20120913/acquire-and-release-semantics/>, and the rest of his series on
  lock-free programming.
- Dmitry Vyukov, "Bounded MPMC queue",
  <https://www.1024cores.net/home/lock-free-algorithms/queues/bounded-mpmc-queue>.
- Leslie Lamport, "Specifying Concurrent Program Modules", *ACM Transactions on Programming
  Languages and Systems* 5(2), 1983. The origin of the lock-free SPSC queue argument.
- Herb Sutter, "atomic<> Weapons: The C++ Memory Model and Modern Hardware", C++ and Beyond
  2012 (video). Two hours that make memory orders concrete.
- Clang documentation, "ThreadSanitizer", <https://clang.llvm.org/docs/ThreadSanitizer.html>.
- cppreference: `std::memory_order`, `std::jthread`, `std::stop_token`,
  `std::condition_variable_any`, `std::latch`, `std::barrier`.
