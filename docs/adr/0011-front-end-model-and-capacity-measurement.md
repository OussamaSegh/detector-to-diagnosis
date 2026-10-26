# 0011. Front-end dead time in the simulator, and capacity measured with a replayed stream

Date: 2026-10-25
Status: Accepted

## Context

Chapter 11 asks two questions of MiniDAQ: what the scanner's count-rate curve looks like
(trues, scatters, randoms and NECR against activity), and which stage of the chain saturates
first as the activity rises. The first depends mostly on the detector front end: its dead
time, the unit that shares it and pile-up. The second depends on the software's capacity
with realistic data. The sorter's work depends on how many singles pass the energy window and
how many windows hold several singles, so synthetic words with uniform energies
(`PacedSource`) say little about it.

The dead time of your scanner's front end, its unit and behavior are not known to the book
(assumption: confirm with team), so the model must be configurable and its parameters recorded with
every measurement.

## Options

For the dead-time model:

1. **A stage in the simulator** (`sim::DeadTime`) applied to the simulator's time-ordered
   singles before anything else sees them, as the electronics would.
2. **A stage in the acquisition pipeline.** It would run on real data too, but the real
   front end has already applied its dead time; a second one would be wrong, and the
   pipeline would carry code that only simulations need.
3. **Analytical correction only** (`recorded_rate`, `true_rate`) without simulating events.
   It gives rates, not the energies that pile-up changes, and not the coincidence losses
   that come from two singles each having to survive.

For the capacity measurement:

1. **Replay a recorded simulator stream through the real pipeline in real time**
   (`sim::ReplaySource` in `minidaq_latency`), and report each stage's busy share of the wall
   time.
2. **Benchmark each stage in isolation** (`bm_sorter` and the others). Repeatable, but blind
   to the other threads sharing the machine and to the queues between stages.
3. **Drive the pipeline as fast as possible** and report the throughput. It finds the
   maximum, but not which stage limits it or how close each stage is at a given rate.

## Decision

Dead time is option 1: `sim::DeadTime`, non-paralyzable or paralyzable, per block or per
crystal, with optional pile-up, exact for any chunking and releasing events in time order.
The analytical models of option 3 are kept next to it as `recorded_rate` and `true_rate`,
for tests and for correction. `minidaq_sim` exposes the model on its command line and
prints one `countrate` line per run for the measurement scripts.

Capacity is option 1: `ReplaySource` loops a recording with its time stamps shifted by
whole loops, at a chosen rate or in real time, and `minidaq_latency --words` prints each
stage's busy percentage, stalls, idles and drops after its latency table. The replay
source's own busy time is reported but is not a limit of the pipeline. Isolated benchmarks
(option 2) remain the regression gate for single stages.

## Consequences

### Positive

- The count-rate harness (`measurements/ch11/countrate.py`) separates what each loss costs,
  because the truth of every coincidence is known: at 100 MBq of the NEMA-style source, a
  1 µs block dead time costs a third of the NECR and pile-up more than 40% of the rest
  (`measurements/ch11/frontend.txt`).
- The simulated losses agree with the analytical models applied to each block's own rate
  (20.9% and 23.5% at 100 MBq), which validates the stage against the formulas
  (SRS-DTM-001 to 008).
- The first software bottleneck is measured, not guessed: the pair stage, at about 70 M
  singles per second on the book's VM (`measurements/ch11/bottleneck.txt`).

### Negative

- Pile-up adds the whole energy of a lost event, the worst case; a real front end adds only
  the light inside its integration window, and may reject pile-up. The model overstates
  pile-up losses until it is replaced by your scanner's measured behavior.
- The replay source spends about 65% of a core reading the clock and copying at high rates.
  On a machine with fewer cores than threads that time competes with the stages it feeds.
- A replayed loop repeats the same singles; a run longer than the recording sees the same
  multiples pattern again, which is harmless for capacity but not for statistics.
