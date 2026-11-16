# 0037. Watch the time base from the data and from the hardware's lock status

Date: 2026-11-16
Status: Accepted

## Context

A coincidence compares two time stamps from two detector blocks, so every block must count the
same time. The scanner gets that from a distributed reference clock: each board locks a local
oscillator to it with a phase-locked loop (PLL) and a common pulse starts all counters together
(Chapter 38). The timing calibration (Chapter 26) then removes each crystal's fixed delay once.

Nothing in MiniDAQ 1.x notices when that stops being true during a run. A PLL that loses lock
and locks again can come back a few hundred picoseconds away; a board that resets restarts its
counter; a reference that drifts moves one group of boards against another. The order of the
singles is kept, so the order checks of H-02 (RC-06, RC-07) see nothing. The coincidences that
are still found have wrong time differences, true coincidences near the window's edge are lost,
the delayed window no longer estimates the randoms of the prompt window exactly, and a time of
flight (Chapter 39) puts each event at the wrong place along its line. The hazard is H-02, whose
residual named this gap.

## Options

1. **Trust the hardware.** Read each board's PLL lock status and count of lock losses (register
   map 1.3) and treat the run as faulty after a lock loss. Simple, and it reacts at once. It sees
   only what the firmware detects: a reference that drifts while every PLL follows it faithfully,
   a counter restarted by a reset that is not a lock loss, or a cable whose delay changes with
   temperature are all "locked".
2. **Measure from the data.** The mean time difference of the true coincidences between two
   blocks depends only on the source and the geometry, so a change of it during a run is a change
   of the blocks' clocks. Measure it per pair of blocks and interval, and solve for one offset per
   block. It sees every cause, whatever its origin, and says which block moved. It needs counts:
   it reacts after an interval (1 s by default) and cannot see a block in no coincidence pair or a
   shift common to all blocks, which changes no coincidence anyway.
3. **Both.**

## Decision

Option 3. The lock status is the fast, specific signal of the failure the hardware knows about;
the monitor of the data is the independent check of the property that matters, the agreement of
the time stamps, and catches what the firmware cannot. Each is a risk control of H-02: RC-53 for
the monitor, RC-54 for the lock status. Either one at fault makes the run's integrity verdict
"not complete", so a consumer of the data reads one field, as for losses (RC-01).

The monitor's details:

- Trues, not prompts. Randoms have a flat time difference whose mean is the window's center; they
  would dilute a shift by the fraction of randoms. The sums of the delayed window, which holds
  randoms only, are subtracted from those of the prompt window.
- Only differences within +-2 ns are used. Each random adds noise in proportion to the square of
  its difference, and the trues of a scanner of 300 mm are within about +-1 ns plus the
  resolution.
- A reference per pair from the first two intervals of the run, not an absolute zero: the mean
  depends on where the activity is. A fixed offset present from the start is the timing
  calibration's business (Chapter 26), and the lock status covers a board that starts unlocked.
- Weighted least squares with a mean of zero per group of connected blocks, and chi2 per degree of
  freedom as a check that block clocks explain the shifts at all.
- Levels against limits and against the estimate's own uncertainty (5 standard deviations by
  default), so that a block with few counts does not raise false alarms.

## Consequences

### Positive

- A block whose clock moves during a run is found within an interval (1 s by default) and named,
  whatever the cause; a lock loss that the firmware sees is found at the next slow-control cycle.
- The run's integrity verdict says that its times cannot be trusted, so reconstruction and
  quality control need not know the monitor.
- The status shows each block's offset with its uncertainty, which the service engineer uses to
  find the board, and a chi2 that says whether block clocks explain the shifts at all.

### Negative

- One more computation per interval in the pair stage: the inverse of a 72 by 72 matrix, measured
  in `measurements/ch38/`. Per coincidence, two block numbers and six additions.
- The status gains `timing` (control API 3.1, new fields only) and each board its clock status;
  the integrity verdict gains two counters; the configuration gains `timing_monitor` (schema 2.1,
  optional, with defaults).
- A shift common to all blocks and a block in no coincidence pair cannot be seen. A synthetic
  source that pairs each crystal only with the opposite one gives groups of two blocks, where a
  step shows on both blocks at half its size: the monitor reports what can be known.
- The limits (100 ps warning, 250 ps alarm) are assumptions to confirm for a real scanner; a
  scanner with time of flight needs tighter ones.
