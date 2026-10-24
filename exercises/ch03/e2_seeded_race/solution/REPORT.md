# Exercise 3.2 report: two seeded races

Build: `tsan` preset (Clang 18, -O0, `-fsanitize=thread`), `TSAN_OPTIONS=halt_on_error=1`.

## Race 1: lost updates in `record()`

```
WARNING: ThreadSanitizer: data race
  Write of size 8 at 0x7ffec91e6618 by thread T2:
    #0 ex::EnergyMonitor::record(float) .../starter/monitor.hpp:24:48
  Previous write of size 8 at 0x7ffec91e6618 by thread T1:
    #0 ex::EnergyMonitor::record(float) .../starter/monitor.hpp:24:48
  Location is stack of main thread.
```

**Cause.** `bins_[b] += 1` and `total_ += 1` are read-modify-write sequences on plain
integers, executed by two decoder threads. Two threads can read the same old value and both
write old + 1, so counts are lost. The non-TSan test usually catches this one too, because
the totals come out short (a lost-update race has a visible symptom).

**Fix.** `std::atomic<std::uint64_t>` with `fetch_add(1, std::memory_order_relaxed)`. Relaxed
is enough: atomicity of each increment is what matters, and no thread uses a count to decide
whether some other memory is ready. (A faster design gives each decoder its own histogram and
merges on read; with two threads hammering the same bins, atomic increments cause the cache
line to bounce, as in Chapter 2.)

## Race 2: window published through a relaxed flag

```
WARNING: ThreadSanitizer: data race
  Read of size 8 at 0x729400002008 by main thread:
    #0 __tsan_memcpy
    #1 ex::EnergyMonitor::current_window(ex::EnergyWindow&) const .../starter/monitor.hpp:39:9
  Previous write of size 8 at 0x729400002008 by thread T1:
    #0 __tsan_memcpy
    #1 ex::EnergyMonitor::publish_window(ex::EnergyWindow) .../starter/monitor.hpp:30:13
  Location is heap block of size 8216 allocated by main thread
```

**Cause.** The flag is atomic, but the store and load are `relaxed`, so they create no
happens-before relation: seeing `has_window_ == true` says nothing about whether the write
to `window_` is visible. Worse, the control thread keeps rewriting `window_` while decoders
read it, so a decoder can see the new `low` with the old `high`. The ordinary test run usually
passes (on x86 an aligned 8-byte copy is a single instruction in optimized builds); in our
TSan build it also observed a torn window once in ten runs before the preset was fixed.

**Fix.** Publish the window itself atomically: `std::atomic<EnergyWindow>` (8 bytes,
lock-free, checked with `static_assert`) with a `release` store and an `acquire` load. The
"has a window" flag is folded into the value (a sentinel with high < low), so there is one
atomic and no ordering between two variables to get wrong. For a larger configuration the
same idea needs a different mechanism: a mutex, a seqlock, or publishing an immutable object
through an atomic pointer.

## How I know it is fixed

- The solution passes both tests under `tsan` with zero reports, 10 runs in a row.
- The fix is argued from the memory model (release/acquire pair), not from "the test passes".

## What surprised me

With the `tsan` preset at -O2 (its original setting) TSan **never** reported race 2 when the
monitor was a stack variable: Clang 18 left the reader's loads uninstrumented. It reported it
every time when the monitor was on the heap or static, and every time at -O0. The test now
uses a heap object and the preset builds at -O0. A clean TSan run is evidence, not proof.
