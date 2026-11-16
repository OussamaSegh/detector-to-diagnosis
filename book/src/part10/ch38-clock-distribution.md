# Clock distribution and the scanner's time base {#ch38}

::: box-why
A coincidence is a comparison of two time stamps taken by two different boards. The sorter's
window is a few nanoseconds wide, a time-of-flight scanner reads meaning into a few hundred
picoseconds, and nothing in the physics makes two boards agree on time: they agree because a
clock is distributed to them, each board locks to it, and a common pulse starts their counters
together. When that stops being true in the middle of a run, the singles stay in order, every
check of the data path is satisfied, and the scan is stored as if nothing happened. This chapter
follows the clock from the reference oscillator to the time stamp, shows how networks synchronize
clocks when no dedicated cable can, and makes MiniDAQ watch its own time base during a run: from
the coincidences it already finds, and from each board's lock status. A step of 300 ps in one
block's clock is named at the end of the next half second; ten healthy runs raise no alarm.
:::

**A day in the life.** A short dip of the mains voltage during an afternoon list resets nothing
that anyone notices. On one of the scanner's 72 detector boards, the phase-locked loop that makes
the sampling clock loses lock for a few microseconds and locks again, 400 ps away from where it
was. The board keeps counting; its singles are in order; the sorter finds as many coincidences as
before, because 400 ps is far inside a window of 4 ns. The time-of-flight reconstruction moves
every annihilation on the lines through that block by 6 cm, and the edge of a small lesion near
the block's side of the patient blurs. The physicist's daily phantom passes the next morning,
because the overnight power cycle relocked the loop where it belonged. Weeks later a service
engineer reads a line in the board's log, "PLL unlock", with a time stamp from that afternoon. The
software had read the board's registers every 100 ms all along; the lock status was simply not one
of them.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Explain what it takes for many boards to stamp times on one time base: a common frequency, a
   common phase and a common start, and what breaks each.
2. Describe a scanner's clock tree, from the reference to each board's phase-locked loop, and say
   what a loss of lock does to the time stamps.
3. Compute a clock's offset and the path's delay from the four time stamps of a Precision Time
   Protocol exchange, and say what an asymmetric path does to the result.
4. Write the proportional-integral servo that steers a clock to its reference, with a step for a
   large offset and a limit that does not wind up.
5. Measure the agreement of the blocks' clocks from the coincidences of a run, and say why the
   delayed window and a reference per pair are needed.
6. Solve for one clock offset per block by weighted least squares, and use chi-square to tell a
   block clock from a fault that no block clock explains.
7. Choose limits for a monitor from its measured noise, and state what it cannot see.

## Prerequisites and estimated time {.unnumbered}

Chapter 8 (coincidences and time of flight), Chapter 10 (the sorter and its delayed window),
Chapter 22 and Chapter 24 (the boards, their registers and the interface control document) and
Chapter 26 (the timing calibration and its least squares). Reading: about 3 hours. Exercises: 6
hours. Milestone: 3 hours. If time is short, do Exercise 38.3.

## One time base for many boards

A time stamp in MiniDAQ is a count of picoseconds on one board's clock. The board's sampling
clock, a few hundred megahertz, drives a counter that gives the coarse time, and a fine time
measurement inside one period (a time-to-digital converter, or a fit to the sampled pulse) gives
the rest. The board knows nothing of any other board. For two of its time stamps to be
comparable with another board's, three things must hold:

- **Frequency.** Both clocks count at the same rate. Two free-running crystal oscillators differ
  by tens of parts per million: after one second they disagree by tens of microseconds, after a
  scan of 20 minutes by tens of milliseconds. Making clocks run at one rate is called
  syntonization.
- **Phase.** At any instant, both counters hold the same value, give or take the cable delays
  that a calibration removes. Making clocks agree on time is synchronization.
- **Start.** Both counters began at the same edge, so that a count means the same instant on
  each. A board that resets its counter on its own keeps the right frequency and the right phase
  of its clock and is still wrong by everything it counted before.

Chapter 26 removed each crystal's fixed delay, the part of the disagreement that stays the same
from run to run: cable lengths, the board's own electronics, the crystal's light collection. That
calibration assumes the three properties above hold during every run, and nothing in MiniDAQ 1.x
checked that they did.

Three words describe how a clock departs from its ideal, and the data sheets of clock parts use
them precisely. **Jitter** is the short-term variation of each edge around where it should be,
picoseconds or less on a good clock; it adds to the coincidence time resolution of Chapter 8 like
any other noise. **Wander** is the slow variation of the same, over seconds to hours, from
temperature mostly. **Offset** is a constant difference of phase, and **skew** the difference of
offsets between two places in a distribution. Jitter blurs; an offset that changes in the middle
of a run moves.

What a moved time base does to the data depends on how much it moved and who reads the times:

- **Time of flight.** The difference of the two photons' arrival times places the annihilation
  along its line, at c Δt / 2 from the line's middle: 15 mm for every 100 ps (Chapter 8). A
  block's clock off by 400 ps moves every event on its lines by 60 mm, toward one end. The next
  chapter builds on this.
- **The window.** A true coincidence whose time difference moves toward the edge of the window
  may leave it. MiniDAQ's window is 4 ns and its trues are within about 1.3 ns, so a few hundred
  picoseconds lose almost nothing; a scanner with a narrow window loses more.
- **The calibration.** Every later step that trusts the delays of Chapter 26 inherits the error,
  including the next calibration if it is made from a run like this one.
- **The order.** A clock that steps backward can make a board's singles go back in time. That is
  the one case the data path already catches: the sorter counts singles out of order and the
  service ends the run in a fault (risk controls RC-06 and RC-07 of hazard H-02). A step forward,
  a drift, or a step backward smaller than the gap between a board's singles keeps the order, and
  nothing catches it.

## The clock tree

Most scanners give every board the same clock by wire. A reference oscillator in the gantry, a
temperature-compensated or oven-controlled crystal of 10 to 100 MHz, feeds a tree of fan-out
buffers, and a cable from the last buffer reaches each board. On the board, a phase-locked loop
(PLL) multiplies the reference into the sampling clock, cleans its jitter and keeps its phase
fixed to the reference. A second signal travels the same tree: a start pulse (also called a sync
or a timing reset) that every board receives on the same reference edge, which clears its counter
so that all counters start together (assumption: confirm with team how the product's boards are
clocked and started). Figure [](#fig-ch38-tree) shows the tree.

```{.figure #fig-ch38-tree src="book/figures/tikz/ch38/tree.tex" caption="How a scanner shares one time base. The reference and the start pulse reach every board through a fan-out; each board's phase-locked loop multiplies the reference into the sampling clock its counter and fine time measurement count. A loop that loses lock and locks again can come back elsewhere." alt="Block diagram: a reference oscillator and a start pulse enter fan-out buffers; cables lead from the fan-out to boards 1, 2 and 72, each with a PLL times N, then a counter with fine time, then time stamps. A note under the fan-out says cables of matched lengths, or delays measured once. A note under the last PLL, in the alarm color, says lock lost, relocked elsewhere: the board's times move." width="95%"}
```

A PLL compares the phase of its output, divided by N, with the phase of the reference, and steers
a voltage-controlled oscillator until the two agree. While it does, it is **locked**, and a lock
detector in the chip says so. When the reference disappears or jumps, the loop loses lock; when
the reference comes back, it locks again, and where it locks depends on the design. A loop whose
dividers are not reset may settle on another edge of the multiplied clock, a whole period away,
or on another phase of a fine phase interpolator, a fraction of one; a board whose fine time
measurement is calibrated against its clock's phase loses that calibration (assumption: confirm
with team what the product's boards do after a relock). In every case the board's time stamps
afterwards differ from before by an amount that nothing in its data stream records.

The tree has two virtues and one weakness. Its virtues: every board's frequency is the
reference's, exactly, because every board is locked to the same oscillator; and the cable delays
are fixed, so a calibration removes them once. Its weakness is the one this chapter is about: a
board that loses lock, a buffer that fails, a cable that is replaced with one of another length,
all change the time base silently, and the only parts that know are the PLL's lock detector and
the data.

### When there is no clock cable: synchronizing over a network

Systems that cannot run a clock cable to every node synchronize over the network they already
have. The **Precision Time Protocol** (PTP, IEEE 1588) does it with an exchange of messages. A
master clock sends a Sync message and notes when it left, t1; the slave notes when it arrived,
t2, on its own clock. The slave sends a Delay_Req message at t3, its time, and the master notes its
arrival at t4, its time. If the path takes d in each direction and the slave's clock is ahead of
the master's by θ, then t2 - t1 = d + θ and t4 - t3 = d - θ, two equations in two unknowns
(Figure [](#fig-ch38-ptp)):

```{.figure #fig-ch38-ptp src="book/figures/tikz/ch38/ptp.tex" caption="One exchange of the Precision Time Protocol. Two time stamps on each clock give the offset and the delay, provided the path takes as long in both directions; the slave's turnaround time cancels." alt="Timeline diagram with the master's time line on the left and the slave's on the right. Sync goes from the master at t1 to the slave at t2; Delay_Req goes from the slave at t3 to the master at t4. Beside it: t2 minus t1 equals d plus theta, t4 minus t3 equals d minus theta, theta is half the difference and d half the sum. A note: a path slower one way by a errs by a over 2." width="90%"}
```

θ = ((t2 - t1) - (t4 - t3)) / 2 and d = ((t2 - t1) + (t4 - t3)) / 2. The derivation assumes
that the path is symmetric. If it takes a longer one way than the other, half of a goes into θ,
and no exchange of messages can tell: the protocol can only measure the round trip. Everything
that makes PTP accurate is about keeping the two directions equal and the time stamps exact:

- **Hardware time stamps.** The network card stamps a message as it crosses the wire, not when
  the operating system gets around to it. Software stamps are good to microseconds; hardware
  stamps to tens of nanoseconds or better.
- **Switches that take part.** A switch queues messages for a variable time, which differs by
  direction. A transparent clock in the switch measures how long each message stayed and writes it
  into the message; a boundary clock is a slave on one side and a master on the other.
- **Filtering.** Queueing only ever adds delay. The exchanges with the shortest round trip met the
  least of it, so a client keeps those and drops the others (Exercise 38.1).

The slave then steers its clock with a servo, usually proportional-integral: the proportional term
answers the offset now, and the integral term learns the clock's frequency error, so that a clock
that runs fast by a constant amount ends at offset zero instead of at the offset whose
proportional answer cancels the error. An offset too large to slew in reasonable time is stepped
at once, and while the answer is at its limit the integral must not keep growing, or the clock
overshoots for as long afterwards (Exercise 38.2). Linux's `ptp4l` works this way.

PTP on ordinary Ethernet with hardware time stamps reaches tens of nanoseconds: enough to tie a
scanner's time to the hospital's, far from enough for a coincidence. **White Rabbit**, developed
at CERN for accelerators and adopted into the 2019 edition of IEEE 1588 as its high accuracy
profile, adds two things: the frequency travels with the data, recovered from the Ethernet
signal itself (synchronous Ethernet), and the phase of that recovered clock is measured to
picoseconds. It distributes sub-nanosecond time over kilometers of fiber, and it is one way to
clock a scanner whose boards are far apart or whose designers want the clock and the data on one
fiber. Whatever the method, the result on the board is the same as in Figure [](#fig-ch38-tree): a
local oscillator steered to a reference, with a lock that can be lost.

## What the boards report: register map 1.3

MiniDAQ's boards now say whether their clock is locked. Firmware 1.4 implements register map 1.3,
which adds one read-only register (`hw/feb.toml`, ICD-FEB version 5):

| Register | Address | Field | Meaning |
|---|---|---|---|
| `clock_status` | 0x034 | `pll_locked` (bit 0) | 1 while the loop that makes the sampling clock is locked |
| | | `lock_losses` (bits 16 to 31) | times the loop lost lock since `trigger_enable` was last set; stays at 65,535 |

A flag alone would not do: a loop that loses lock and locks again between two reads of the slow
control, 100 ms apart, would never be seen unlocked. The count is kept by the firmware, in the
loop's own clock domain, and starts again at every trigger enable, like `datagrams_sent` of
Chapter 24, so that the count the software reads during a run is the run's (assumption: confirm
with team that the firmware counts a loss that ends before the next read).

The slow control reads the register in every cycle, after it has switched the triggers, so that
in the cycle that starts a run the count is already the new run's:

```{.cpp include="minidaq/src/hw/slow_control.cpp" snippet="clock-status"}
```

Three things follow from it, each a decision. A board whose clock is not locked keeps a run from
starting: `not_ready()` says "board 3 (slot 7) has no locked clock", and the service refuses the
start as it would for a bias that is still ramping. A loss of lock during a run is not a fault of
the board: the SiPMs are not at risk and the bias stays on; it is a fault of the data, so the
service records an audit event the moment the count grows, and the run's integrity verdict counts
the losses:

```{.cpp include="minidaq/src/control/acquisition_service.cpp" snippet="clock-audit"}
```

The service looks only after the boards have confirmed their triggers: before, a board's count
may still be the previous run's. A board with older firmware has no clock status; the software
reads nothing, refuses nothing, and reports `null`. This is risk control RC-54 of hazard H-02.

The lock status is fast and specific, and it is blind to everything the lock detector does not
see: a reference that drifts while every loop follows it faithfully, a counter restarted by a
reset that is not a loss of lock, a cable whose delay changes with temperature, a board replaced
by one with another delay. For those, the software has to look at the times themselves.

## Watching the time base from the data

The coincidences of a run already contain the test. Take two blocks, a and b, and the true
coincidences between them. Each has a time difference d = t_b - t_a, the difference of the two
photons' flight times plus the difference of the two boards' clocks plus noise. For a source that
does not move, the distribution of the flight-time differences between two given blocks does not
change during the run, so its mean m_ab does not either. If block b's clock moves by x, every
coincidence of the pair (a, b) moves by +x, every coincidence of a pair (b, c) by -x, and nothing
else changes. A change of the mean time difference of a pair of blocks is a change of their
clocks, and the run measures it for free.

Three details turn the idea into a measurement:

- **Trues, not prompts.** The prompt window holds randoms too, pairs of photons from different
  annihilations whose time difference is anything within the window. Their mean is the window's
  middle, so they dilute a shift by the fraction of randoms: with 30% randoms, a step of 300 ps
  would look like 210. The delayed window of Chapter 10 holds randoms only, as many as the prompt
  window on average. Subtracting its sums from the prompt window's leaves the sums of the trues.
- **Only near the middle.** Each random adds noise in proportion to the square of its time
  difference, and the sorter's window is wider than the trues need. The monitor uses only
  differences within ±2 ns, prompts and delayeds alike; the trues of a scanner of 300 mm are
  within about ±1 ns plus the resolution.
- **A reference per pair, not zero.** The mean of a pair is not zero: it depends on where the
  activity is. The first intervals of the run give each pair its reference r_ab, and later
  intervals give the shift s_ab = m_ab - r_ab. A constant offset present from the start is not a
  change and is not seen; it is the timing calibration's business.

The monitor sits in the pipeline's pair stage, which hands it every batch of coincidences the
sorter found. Per coincidence it does a handful of operations: two block numbers, a lookup of the
pair, and three additions to the sums of prompts or of delayeds:

```{.cpp include="minidaq/src/processing/timing_monitor.cpp" snippet="record"}
```

The sums are whole picoseconds in 64-bit integers, exact for any run, and the pair's index comes
from a table of 72 by 72 entries. The first version computed the index and accumulated doubles,
and the CI's performance gate, which runs the pipeline benchmark of Chapter 5 on one CPU, found
the whole pipeline 7.4% slower: the gate's limit is 5%. The integers and the table brought the
cost to about 3% of that benchmark, 9.7 ns per coincidence measured alone. A monitor that runs on
every coincidence of every run is part of the hot path, and is measured like it.

The defaults are in the configuration's `timing_monitor` object (schema 2.1, optional):

```{.cpp include="minidaq/include/minidaq/processing/timing_monitor.hpp" snippet="config"}
```

## From pairs to blocks

At the end of each interval the monitor has a shift and its variance for every pair with enough
trues: some hundreds of pairs for 72 blocks. Each block's clock explains the shifts of all its
pairs at once: s_ab = o_b - o_a for one offset o per block. That is the same problem as the
crystal delays of Chapter 26, at the scale of blocks and repeated in time, and the same least
squares solves it: minimize the sum over pairs of (s_ab - (o_b - o_a))² / var_ab.

Two properties of the problem matter more than the solver. The first is that a shift common to
all blocks changes no pair, so it cannot be estimated: the normal equations L o = r, with L the
Laplacian of the graph whose edges are the pairs, are singular, once per group of blocks connected
by pairs. The monitor fixes each group's mean at zero, which is a statement about what can be
known, not an assumption about the scanner. A block in no pair, or in a group of one, is
unobserved. The second is redundancy. Seventy-two offsets are fixed by hundreds of shifts, so the
shifts must agree with each other, and whether they do is a test. Around any loop of pairs, the
shifts of block clocks sum to zero; a fault that is not a block clock, such as two cables swapped
between a pair of boards or a geometry that changed, does not (Figure [](#fig-ch38-closure)).

```{.figure #fig-ch38-closure src="book/figures/tikz/ch38/closure.tex" caption="The signature of a block clock. When block B's clock moves by x, its pairs move by +x and -x and the shifts around any loop sum to zero; when one pair alone is wrong, they do not, and no set of block offsets explains them." alt="Two triangles of blocks A, B and C. Left, B is highlighted; the pair A-B is labeled plus x, B-C minus x, A-C zero; the note says around the loop x minus x plus zero equals zero, one offset per block explains it. Right, only the pair A-B is highlighted, labeled plus y, the others zero; the note says around the loop y is not zero, no offsets explain it, chi2 grows." width="75%"}
```

The weighted residual, chi-square, measures it. Divided by its degrees of freedom (the pairs used
less the unknowns, which are the observed blocks less one per group), it is about 1 when block
clocks explain the shifts within their variances, and larger when something else is going on.
Radio astronomers use the same idea, under the name closure phase, to see through the phase
errors of each antenna of an interferometer.

The solver's interface takes the pairs and returns the offsets, their standard deviations, the
groups and chi-square:

```{.cpp include="minidaq/include/minidaq/processing/timing_monitor.hpp" snippet="solve"}
```

For 72 blocks it builds the 72 by 72 normal matrix, adds J / n over each group (J a block of
ones), inverts it by Gauss-Jordan elimination and takes the covariance of the offsets from the
inverse, less J / n. That costs 0.3 ms, once per interval. Chapter 26's 18,432 crystals needed
conjugate gradients instead; the 72 blocks can afford the covariance, and the covariance is what
turns an offset into a decision.

### Levels: a limit and a significance

An offset is a number with an uncertainty. With intervals of 0.5 s at the measurement's activity,
each block's standard deviation was about 25 ps, so a healthy block's offset ranges over tens of
picoseconds from interval to interval, and across 72 blocks and many intervals some reach more.
A level that compared the offset with a limit alone would fire on noise; one that asked only for
significance would fire on a real but harmless 20 ps once the counts were high. The monitor asks
for both:

```{.cpp include="minidaq/src/processing/timing_monitor.cpp" snippet="close"}
```

A block is at alarm when its offset is above 250 ps and above 5 standard deviations, at warning
above 100 ps and the same significance, and normal otherwise. The limits are assumptions, chosen
for a scanner without time of flight: 250 ps is a sixth of the trues' spread in time and moves a
time-of-flight position by 37 mm. A scanner with time of flight needs tighter limits and, for
those, more counts per interval (assumption: confirm with team the limits for the product). The
status reports, per block, the level, the latest offset and its standard deviation, the largest
offset of the run, the intervals at alarm and the time of the first; for the scanner, the worst
level, the pairs and groups used, chi-square per degree of freedom, the intervals with any block
at alarm and the blocks that were at alarm. The integrity verdict counts those intervals as a
loss (RC-53), so a run whose clocks moved is stored as incomplete, the same field a consumer reads
for lost packets.

## What the monitor finds

The measurement `measurements/ch38/time_base.py` runs each case the way of a real run:
`minidaq_send` simulates the scanner with a cylinder source of 1.5 MBq and sends the singles over
UDP in real time to `minidaq_server`, whose pipeline sorts them and runs the monitor with
intervals of 0.5 s. The simulator gives block 29 a clock error, which `minidaq_send --block-clock`
sets: an offset, a drift and a step at a given time. The clock error is applied where a real
board would apply it, to the time stamp of every single of that block, after the physics and
before anything that the software sees.

| Fault of block 29 | Level at the end | Its offset, ps | First alarm, s | Others' largest, ps | chi2/dof |
|---|---|---:|---:|---:|---:|
| step of 50 ps at 2.0 s | normal | 59 ± 26 | never | 103 | 1.08 |
| step of 100 ps | normal | 108 ± 26 | never | 102 | 1.08 |
| step of 150 ps | warning | 157 ± 26 | never | 101 | 1.08 |
| step of 200 ps | warning | 207 ± 26 | never | 100 | 1.08 |
| step of 300 ps | alarm | 305 ± 26 | 2.5 | 100 | 1.08 |
| step of 600 ps | alarm | 601 ± 26 | 2.5 | 104 | 1.08 |
| drift of 0.1 ppb (100 ps/s) | alarm | 327 ± 26 | 3.5 | 100 | 1.08 |

The offsets are within one standard deviation of the steps, and Figure [](#fig-ch38-steps) shows
them against the limits. A step of 300 ps or more at 2.0 s is at alarm at 2.5 s, the end of the
first interval after it; the steps of 150 and 200 ps are at warning, the smaller ones normal.
The drift reaches the alarm limit at 3.5 s. No other block reaches a warning: the largest offset
of the other 71, about 100 ps, is within their 5 standard deviations. Chi-square per degree of
freedom stays near 1: a single block's clock explains the shifts, as it should. The runs use the
same seed, so the noise of the other blocks is the same in every row.

```{.figure #fig-ch38-steps src="book/figures/plots/ch38/steps.py" caption="What the monitor estimated for a step of block 29's clock, with five standard deviations, against the limits; the gray band is the largest offset any block reached in ten healthy runs." alt="Scatter plot of the offset estimated against the step injected, 50 to 600 ps, close to the diagonal. Points at 50 and 100 ps are normal, 150 and 200 ps warning, 300 and 600 ps alarm, each with an error bar of five standard deviations, about 130 ps. Dotted lines mark the warning limit at 100 ps and the alarm limit at 250 ps. A gray band from minus 115 to 115 ps is labeled healthy runs: every block within 115 ps." width="85%" inputs="measurements/ch38/time_base.txt"}
```

Then ten healthy runs of 4 s, each with its own seed: 60 evaluated intervals of 72 blocks, 4,320
block intervals. None was at alarm, and no block ended a run at warning. The largest offset any
block reached was 115 ps, above the warning limit and below 5 of its standard deviations: the
significance is what kept it normal. Chi-square per degree of freedom was between 0.99 and 1.28.
Ten runs bound the false alarm rate of a block interval only loosely, below about 1 in 1,400 with
95% confidence; the margin is better shown by the noise, a standard deviation of about 25 ps
against a limit of 250 ps, ten of them, and the requirement of 5 at the same time.

Two numbers set the trade-off of a configuration. The standard deviation of an offset falls as
one over the square root of the trues of its pairs, so it falls with the activity and with the
interval's length; and the interval's length is the delay of the alarm. A scanner at a clinical
rate has many more trues per pair than this measurement's, and can use shorter intervals or
tighter limits at the same false alarm rate. The monitor's minimum of 10 trues per pair and
interval keeps a pair with too few out of the fit; the weights already give it little say.

The system tests check both directions through the whole server: a step of 600 ps in block 29
names that block alone, at the expected time, and makes the run incomplete; a healthy run raises
no alarm and connects every block in one group:

```{.python include="minidaq/tests/system/test_readout_system.py" snippet="clock-step"}
```

## What it costs and what it cannot see

The monitor's cost, measured by `bm_timing_monitor` on the machine of the measurement: 9.7 ns per
coincidence in the pair stage, and 0.3 ms per interval for the fit, on the same thread. At
200,000 coincidences per second that is 2 ms of every second, 0.2% of one core, plus the fit.

What it cannot see is part of its specification, and the hazard file says it in H-02's residual:

- **A constant offset from the start.** The reference is the run's own first intervals. A board
  that starts the run off, because it was replaced or its cable changed, looks normal; the timing
  calibration and the daily quality control are the controls for it, and the lock status catches
  a board that starts unlocked.
- **A shift common to every block.** It changes no coincidence, and matters to nothing that
  compares times within the scanner. It does matter to a time stamp compared with the outside
  world, such as the start of a gated acquisition; that is the network's synchronization, above.
- **A shift below the limits, and the interval in which a shift happens.** The data of the
  interval that found the step, and of the ones before an alarm, are not corrected: the monitor
  reports, it does not repair. Correcting the times would be a second, much larger change (a
  correction applied to the data needs its own verification), and a run whose times are known to
  have moved is better repeated than mended.
- **A source that moves.** The reference assumes the distribution of the activity does not change
  during the run. A bed that moves between positions, or a tracer that redistributes over minutes,
  changes the pairs' mean time differences without any clock moving. Chi-square shows such shifts
  as ones that block clocks do not explain, which is a reason to look, not proof of a clock fault;
  a scanner with several bed positions needs a reference per position (assumption: confirm with
  team; MiniDAQ does not implement it, and its measurements use a static source).

The risk file records two new controls for the sequence "the time base of one block moves during a
run", added to H-02: RC-53, the monitor, and RC-54, the lock status. Each covers what the other
misses. The lock status reacts within a slow-control cycle and only to what the loop's detector
sees; the monitor reacts within an interval and to any cause, if it changes the times by more than
its limits. A new failure mode comes with them: a false alarm stores a good run as incomplete. The
levels require both the limit and 5 standard deviations to keep it rare, and the measurement of the
healthy runs is its evidence.

::: box-mistakes
- **Trusting a lock flag that is read every 100 ms.** A loop that unlocks and relocks between two
  reads is never seen; the firmware must count losses.
- **Treating a lost lock as a fault of the board.** The bias and the SiPMs are fine; switching
  them off loses the patient's scan for nothing. It is a fault of the data, recorded as such.
- **Watching prompts instead of trues.** Randoms dilute every shift by their fraction; subtract
  the delayed window.
- **Comparing with zero instead of with the run's own reference.** A pair's mean time difference
  depends on where the activity is; only its change says anything about clocks.
- **Solving pair by pair, or along a spanning tree.** It throws away the redundancy that both
  lowers the noise and tells a block clock from something else.
- **A limit without a significance, or a significance without a limit.** One fires on noise, the
  other on harmless shifts once the counts are high.
- **An exact equality on the monitor's output in a test.** The offsets are estimates; tests check
  them against their own standard deviations and against ranges.
- **A monitor on the hot path that nobody measured.** It ran on every coincidence and cost the
  pipeline 7.4% before the gate saw it.
- **Correcting the times in the data from the monitor's estimate.** A correction of the data is a
  change with its own verification; report, and decide whether to repeat the scan.
:::

## What this leaves out

The design of PLLs and clock-cleaner chips (loop bandwidth, phase noise and their effect on the
coincidence time resolution); the distribution of a clock over the fiber that also carries the
data, with clock recovery at each end; the PTP profiles and their configuration, including the
hospital's own time service and the time stamps of DICOM objects (Chapter 35); calibrating the
cable delays of the tree with a dedicated source rather than with the coincidences of a cylinder;
the temperature dependence of cable and buffer delays, which a long scan can show as a slow drift;
correcting a measured drift during a run; and the reference per bed position that a multi-position
scan needs. D. Mills's book on network time and the White Rabbit papers in the further reading
cover the network side; F. Gardner's book the loops.

::: box-regulated
- **Risk control.** ISO 14971 clause 7.1: the monitor (RC-53) and the boards' clock status (RC-54)
  are protective measures for the new sequence of H-02, "the time base of one block moves during a
  run"; their effectiveness is verified by tests and by `measurements/ch38/`. A false alarm is a
  new hazardous situation's cause in itself only in the sense that it loses a good scan; the
  measurement of healthy runs is the evidence that it is rare.
- **Requirements.** IEC 62304 clause 5.2: SRS-TIM-001 to SRS-TIM-006 and SRS-CFG-016, each with
  its test; the monitor's limits are requirements with assumptions to confirm, not constants in
  code.
- **Interfaces.** The interface control document with the firmware (ICD-FEB version 5) records the
  new register, which firmware implements it, and what the software does with it; the register map
  is generated from `hw/feb.toml`, as in Chapter 22.
- **Change control.** CR-0031 with its impact analysis: control API 3.1 and configuration schema
  2.1 add fields only (ADR 0003), and register map 1.3 adds a register without changing any.
- **Records of this chapter.** CR-0031, ADR 0037, SRS version 34, H-02 with RC-53 and RC-54,
  ICD-FEB version 5, `measurements/ch38/`.
:::

::: box-askteam
1. How are our boards clocked: a reference by cable, a recovered clock on the data fiber, or PTP?
   Where is the reference, and what is its stability?
2. What does a board's PLL do after a loss of lock: does it come back on the same phase, and does
   the firmware recalibrate the fine time?
3. Does the firmware count losses of lock, in which clock domain, and since when? Is the count in
   the data stream, in a register, or only in a log?
4. Which events reset a board's time counter, and does the software learn about each?
5. What timing limits does our time-of-flight reconstruction need, per block and per crystal, and
   who owns them?
6. How is a scan with several bed positions handled by anything that compares a run with its own
   beginning?
7. When the time base is found to have moved, is the scan repeated, corrected, or read with a
   caveat? Who decides, and how is it recorded?
8. Which daily quality control would find a constant offset of one block that started with a board
   replacement?
:::

## Exercises {.unnumbered}

**Exercise 38.1 (E): A clock's offset from four time stamps.** *Goal:* compute a slave clock's
offset and the path delay from one PTP exchange, and estimate the offset from many exchanges
whose delays include queueing. *Starter:* `exercises/ch38/e1_ptp_offset/starter/ptp.py`, which
takes t2 - t1 as the offset and averages every exchange. *Acceptance:* `tests/test_ptp.py` passes:
a symmetric path gives the offset and the delay exactly, an asymmetric one errs by half the
asymmetry, the turnaround does not matter; from 1,000 exchanges with exponential queueing of 5 us
on average, one in ten without, the estimate is within 5 ns. *Time:* 1 hour.

**Exercise 38.2 (M): The servo that keeps a clock on time.** *Goal:* a proportional-integral servo
that brings a clock's offset to zero, steps an offset too large to slew, and does not wind up at
its limit. *Starter:* `exercises/ch38/e2_clock_servo/starter/servo.py`, proportional only and
never stepping. *Acceptance:* `tests/test_servo.py` passes on a simulated clock: 20 ppm fast ends
within 1 ns after 80 s and learns a change to 23 ppm; 5 ms off is within the step threshold after
one update; 80 us off with a limit of 2,000 ppb overshoots by less than 8 us; with 50 ns of noise
the offset varies by less than 80 ns rms. *Time:* 2 hours.

**Exercise 38.3 (H): Block offsets with closure.** *Goal:* one clock offset per block from the
shifts of pairs, with uncertainties, groups and chi-square, as MiniDAQ's `solve_block_offsets`
does. *Starter:* `exercises/ch38/e3_closure/starter/offsets.py`, which walks a spanning tree from
the first block of each group. *Acceptance:* `tests/test_offsets.py` passes: exact shifts give the
offsets with a mean of zero; one pair of variance 400 gives sigma 10; eight blocks with noisy pairs
are within 10 rms of the truth, one bad pair weighted down; two groups are solved apart and a lone
block is unobserved; one swapped pair gives chi-square per degree of freedom above 50. *Time:* 3
hours.

## MiniDAQ milestone: a time base that is watched {.unnumbered}

::: box-milestone
**Goal.** Every run reports each block's clock offset with its uncertainty and each board's clock
lock; a run whose time base moved is stored as incomplete and named in the audit trail.
**Start:** tag `ch37`. **End:** tag `ch38`.
:::

1. Write change request CR-0031 and ADR 0037; add SRS-TIM-001 to SRS-TIM-006 and SRS-CFG-016 (SRS
   version 34), and RC-53 and RC-54 to H-02.
2. Add the time base monitor (`processing/timing_monitor`) and its tests; record every batch of
   the pair stage in it and flush it at the end of the run.
3. Add `timing_monitor` to the configuration (schema 2.1) and `timing` to the status (control API
   3.1); count the intervals at alarm in the integrity verdict.
4. Give the simulator a clock per block and `minidaq_send --block-clock`; add the two system tests.
5. Add `clock_status` to `hw/feb.toml` (register map 1.3), regenerate the header and the table, and
   update ICD-FEB; read it in the slow control, refuse a start without lock, and record a loss
   during a run.
6. Measure (`measurements/ch38/`), check the pipeline benchmark against the performance gate, and
   add Exercises 38.1 to 38.3.

**Definition of done.** The unit and system tests pass, including the two of the time base;
`docs.srs`, `docs.trace`, `docs.baseline`, `docs.changes`, `docs.risk` and `docs.regmap` pass; the
performance gate passes; every starter of the chapter fails. Tag `ch38`.

## Check yourself {.unnumbered}

1. What three things must two boards share for their time stamps to be comparable, and what breaks
   each?
2. What is the difference between jitter, wander and an offset, and which of them does this
   chapter's monitor look for?
3. What can a phase-locked loop's time stamps do after it loses lock and locks again?
4. Why does the board count lock losses instead of only reporting a flag?
5. From the four time stamps of a PTP exchange, derive the offset and the delay. What does an
   asymmetric path do to the offset, and why can no exchange of messages measure it?
6. Why does a proportional servo leave a constant offset on a clock that runs fast, and what does
   the integral term learn?
7. Why does the monitor use trues rather than prompts, and how does it get them?
8. Why is each pair compared with its own reference rather than with zero? What does that make
   invisible?
9. Why are the block offsets only determined up to a constant per group, and how does the monitor
   fix it?
10. What does chi-square per degree of freedom tell you that the offsets do not?
11. Why does a level need both a limit and a significance?
12. Which faults does the lock status catch that the monitor does not, and the other way round?

## Summary {.unnumbered}

- Boards stamp comparable times only if they share a frequency, a phase and a start; a scanner
  distributes a reference and a start pulse, and each board's PLL locks its sampling clock to it.
- A loop that loses lock and locks again can come back elsewhere: the board's singles stay in
  order, the coincidences stay in the window, and the times are wrong by an amount nothing
  records.
- PTP synchronizes clocks over a network from four time stamps, exact for a symmetric path; White
  Rabbit adds the frequency on the data link and picosecond phase measurement for sub-nanosecond
  time.
- Register map 1.3 gives each board's lock and its lock losses since the trigger enable; MiniDAQ
  starts no run without lock, records a loss during a run in the audit trail, and counts it in the
  integrity verdict (RC-54).
- The mean time difference of the trues between two blocks changes only when their clocks do; the
  monitor measures it per pair and interval, with the delayed window removing the randoms and the
  run's first intervals as the reference.
- Weighted least squares gives one offset per block with its uncertainty, up to a constant per
  connected group; chi-square says whether block clocks explain the shifts at all.
- A block is at alarm above 250 ps and 5 standard deviations; a step of 300 ps was named at the
  end of the next interval, and ten healthy runs gave no alarm in 4,320 block intervals (RC-53).
- The monitor cannot see a constant offset from the start, a shift common to all blocks, or a
  shift below its limits, and it assumes a source that does not move.
- It runs on every coincidence: 9.7 ns each, after the performance gate caught a first version that
  slowed the pipeline by 7.4%.

## Further reading {.unnumbered}

- IEEE 1588-2019, *IEEE Standard for a Precision Clock Synchronization Protocol for Networked
  Measurement and Control Systems*, IEEE, 2020: the protocol, its delay mechanisms and the high
  accuracy profile.
- J. C. Eidson, *Measurement, Control, and Communication Using IEEE 1588*, Springer, 2006: the
  protocol's design and its uses by one of its authors.
- M. Lipinski, T. Wlostowski, J. Serrano and P. Alvarez, "White Rabbit: a PTP application for
  robust sub-nanosecond synchronization", IEEE ISPCS 2011.
- D. L. Mills, *Computer Network Time Synchronization: The Network Time Protocol on Earth and in
  Space*, 2nd edition, CRC Press, 2011: clock filters and servos for network time.
- F. M. Gardner, *Phaselock Techniques*, 3rd edition, Wiley, 2005: phase-locked loops, lock and its
  loss.
- W. W. Moses, "Time of flight in PET revisited", *IEEE Transactions on Nuclear Science* 50(5),
  2003: what timing buys a PET scanner, and what it demands.
- A. R. Thompson, J. M. Moran and G. W. Swenson, *Interferometry and Synthesis in Radio Astronomy*,
  3rd edition, Springer, 2017 (open access): closure phase, the same idea for antennas.
- ISO 14971:2019, clause 7 (risk control); IEC 62304:2006+A1:2015, clause 5.2 (software
  requirements).
- ADR 0037, CR-0031 and ICD-FEB in the repository; `measurements/ch38/time_base.txt`.
