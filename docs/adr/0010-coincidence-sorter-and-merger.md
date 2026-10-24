# 0010. A streaming coincidence sorter with configurable policies, and a watermark merger

Date: 2026-10-24
Status: Accepted

## Context

Chapter 10 replaces the placeholder pair stage, which paired consecutive singles, with a
real coincidence sorter. The sorter's rules (window, energy gate, geometry gates, multiples
policy, delayed window) decide the trues and randoms that every later analysis uses, and
`measurements/ch10/validation.txt` shows that the multiples policy alone changes the trues
by about 6% and the bias of the delayed-window randoms estimate from +5% to −8% at 40 MBq.
The rules must therefore be explicit, configurable, recorded with the data and testable
against the simulator's ground truth. The sorter must keep up with 30 M singles per second
inside the energy window on one core (the book's target; assumption: confirm with team),
with bounded latency, and its output must not depend on how the pipeline batches its input.
A scanner has many readout boards whose streams arrive out of step, so the singles must be
merged into one time-ordered stream before sorting.

## Options

For the sorter:

1. **One streaming class, fixed or per-single windows, four multiples policies, gates and a
   delayed window in one pass over a vector buffer.** A window is an index range; a window
   closes when a later single proves it complete.
2. **A pipeline of small stages** (windowing, then policy, then gates). Each stage simpler,
   but the policy needs the gates ("good" pairs), so the stages are coupled anyway, and each
   adds a copy of every window.
3. **Sorting in fixed time blocks** (sort everything in [T, T + Δ), carry state across
   blocks). Simple to parallelize, but every block edge needs the same care as Exercise 10.3,
   and the output depends on Δ unless that care is perfect.

For merging boards:

1. **A k-way heap merge released by a watermark** (the minimum over boards of the latest time
   each has reported), with time markers and a bound `max_skew` on the wait.
2. **Merging by time slices**: gather every board's singles of [T, T + Δ), stable-sort, emit.
   About twice as fast for 24 and 72 boards on the book's VM
   (`measurements/ch10/bench_slice_merge.txt`), with up to Δ more latency.
3. **No merger; require hardware to deliver one ordered stream.** Moves the problem into
   firmware and makes a late board invisible to the software.

## Decision

Sorter option 1: `processing::CoincidenceSorter` (core layer) with `SorterConfig`, checked by
`validate()` before construction. Fixed windows and kill all are the defaults; per-single
windows pair the opener with later singles only, so no pair is considered twice. The delayed
window applies the same policy to (opener, delayed single) pairs. Every single is counted in
`SorterStats`, with an accounting identity in fixed mode. The configuration is schema 1.2's
`sorter` object; the window stays `/pipeline/coincidence_window_ps`.

Merger option 1: `processing::StreamMerger`. It is specified single by single (release when
earlier than the watermark; ties by `TimeOrder`, then board, then the board's own order), which
makes its tests and its fuzz properties simple. Option 2 is recorded as the faster
alternative for many boards (Exercise 10.5); a system with more than about 20 boards and a
throughput problem should switch to it, keeping the same watermark logic and counters.

## Consequences

### Positive

- With the Chapter 8 truth counter's rules the sorter finds exactly its prompts
  (SRS-SRT-010); the output is the same for any chunking (SRS-SRT-008), which lets the
  pipeline batch freely and Exercise 10.3 parallelize by slices.
- One pass and no allocation in the steady state: 68 M singles offered per second (31 M
  inside the energy window) with the delayed window on (`measurements/ch10/bench_sorter.txt`).
- Late and out-of-order singles are counted in the merger and in the sorter and reach the
  status report.

### Negative

- The delayed-window estimate is biased by an amount that depends on the policy; the
  randoms correction must model it, and the policy must travel with the data (list-mode
  header, Chapter 12).
- The sorter holds the last horizon (delay + window) of singles until a later single or the
  end of the run; a source that goes silent needs a time marker for the sorter to report its
  last coincidences before the run ends (not yet implemented).
- The heap merger is the pipeline's bottleneck for many boards (14 M singles per second for
  24 boards against the sorter's 68 M); the pipeline does not use the merger yet, because
  every source today delivers one ordered stream.
- Pairs whose two crystals share a transaxial position are rejected by the field-of-view cut;
  a real scanner would decide them with the axial geometry.
