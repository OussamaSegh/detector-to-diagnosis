# Coincidence sorting algorithms {#ch10}

::: box-why
The coincidence sorter is the heart of the DAQ, and among the first things a DAQ engineer works on.
Every number the physicists and the clinicians later look at, sensitivity, count-rate curves,
randoms fractions, the image itself, is computed from the pairs the sorter keeps. Its rules are few:
a window, an energy gate, a geometry gate, a policy for windows with more than two singles, and a
delayed window for the randoms. Each rule is a choice with measurable consequences, and the same
stream sorted with two policies gives trues and randoms that differ by several percent at high
activity. This chapter builds a streaming sorter that is exact, fast and the same however its input
is chunked, a merger for the streams of many boards, and the validation against ground truth that
turns "the sorter works" into a measured statement.
:::

**A day in the life.** A physicist brings you two count-rate curves of the same phantom
measurement: one sorted by the current DAQ, one by an offline script from a collaborator.
Below 10 MBq they agree; at 40 MBq the script finds 6% more trues and 30% more randoms.
Both claim to use a 4 ns window. You run both on a short piece of the list-mode data and
compare the pairs one by one. The difference is all in windows with three or more singles:
the DAQ discards them, the script keeps every pair in them that passes the geometry cut.
Neither is wrong. They are two policies, and the randoms correction must match the one that
was used. You add the policy to the list-mode header, write it into the acquisition
protocol, and add a test that sorts a recorded stream with each policy and checks the counts
against stored values. The lesson of this chapter: a sorter is a set of documented
choices, and each one is tested.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Implement a time-sorted sliding-window coincidence sorter in streaming C++ that gives
   the same result however its input is cut into chunks.
2. Handle multiples with documented policies (kill all, take all goods, take the winner of
   goods, keep if only one is good) and explain what each does to trues and randoms.
3. Estimate randoms with a delayed window and from the singles rates, and check both
   against the simulator's ground truth.
4. Merge the streams of many boards that arrive partly out of order, with a watermark and a
   bound on how long to wait.
5. Reach a throughput target on one core, such as 30 M singles per second, with bounded
   latency, and parallelize by time slices without losing or doubling a coincidence.

## Prerequisites and estimated time {.unnumbered}

Chapter 3 (threads), Chapter 5 (benchmarks and profiling), Chapter 8 (the physics of trues, scatters
and randoms, the simulator and its truth counter) and Chapter 9 (time stamps and board clocks).
Reading: about 3.5 hours. Exercises: 12 to 16 hours. Milestone: 6 hours.

## The problem

### The intuition

A positron annihilates and sends two 511 keV photons in nearly opposite directions. Each
photon that is detected becomes a single: a time stamp, a crystal and an energy. The two
singles of one annihilation arrive within a few hundred picoseconds of each other, plus the
time resolution of the detector. A coincidence sorter looks at the stream of all singles,
from all crystals, in time order, and pairs those that are close enough in time. That is
the whole idea. Everything else is about the cases where "close enough" is ambiguous.

Chapter 8 named the three kinds of pairs. A **true** is two photons of one annihilation
that reached the detector unscattered. A **scatter** is two photons of one annihilation,
at least one of which was deflected in the patient, so the line between the two crystals
misses the annihilation. A **random** is two photons from two different annihilations
that happened to arrive within the window. The sorter cannot tell them apart one by one:
it sees only times, crystals and energies. What it can do is apply rules that keep many
trues and few of the others, and estimate how many randoms it kept.

### What the sorter is given

The input is the singles of all boards, merged into one stream in time order. Chapter 9
built the link from one board; a real scanner has many, and the first part of the problem
is to merge their streams (later in this chapter). Each single that reaches the sorter has
passed the front end's own threshold, but not yet the energy window of the sorter.

The rules are:

- A **coincidence window** τ: two singles are candidates if their times differ by at most
  τ. MiniDAQ uses 4 ns, and the window is inclusive: exactly 4,000 ps apart is a pair,
  4,001 is not. (assumption: confirm with team the window your scanner uses; with a
  coincidence time resolution of a few hundred picoseconds a window of a few nanoseconds is
  typical.)
- An **energy window**, applied to each single before it takes part: 435 to 585 keV in
  MiniDAQ's default (assumption: confirm with team), 76 and 74 keV either side of the
  photopeak. Chapter 8's counter used 435 to 650 keV; the tighter upper edge also rejects
  singles in which two photons have piled up (Chapter 11). A scattered photon has lost energy, so
  the window removes many scatters, and with them singles that would only make randoms.
- A **geometry gate** on the pair: two crystals in the same module, or in neighboring
  sectors, cannot see a real annihilation inside the field of view, and a line of response
  that passes outside the field of view is useless for the image.
- A **multiples policy** for windows that hold three or more singles.
- A **delayed window** that counts pairs which cannot be trues, as an estimate of the
  randoms.

The output is a stream of prompt coincidences (those found in the normal window, a mix of
trues, scatters and randoms) and delayed coincidences (randoms only). The reconstruction
uses the prompts as data and the delayed counts, or a model of them, to subtract the
randoms (Chapter 27 does this for real).

### Why the stream must be in time order

A sorter that reads a stream cannot keep all of it. It holds the singles of the windows
that are still open, and it decides that a window is complete when a single arrives that is
too late to belong to it. That decision is only correct if nothing earlier can still
arrive. With singles in time order, the first single later than t + τ proves that the
window opened at t is complete. With singles out of order, no single proves anything: the
partner of a single could be anywhere further down the stream, and the sorter would have to
hold the whole run. This is the first of two questions that this chapter answers, and the
answer shapes everything else: put the singles in order first, with a bounded buffer, then
sort them in one pass with a buffer of a few windows.

What if a single arrives out of order anyway, because a board is late? The sorter has
already closed the windows it would have joined. MiniDAQ's sorter counts such a single in
`out_of_order` and drops it. It does not try to reopen a window: that would make the output
depend on when data arrived rather than on the data. Dropping and counting is the honest
choice, and the merger's job is to make it rare.

::: box-mistakes
- **Applying the energy window after pairing.** A single outside the energy window that
  opens a window, or sits in one, changes which pairs are found. Filter each single first,
  then form windows; the result is the one a reader of your documentation expects.
- **A window that is exclusive on one side and inclusive on the other without saying so.**
  At picosecond resolution, singles exactly τ apart are rare but they occur. Choose,
  document and test the boundary.
- **Reopening windows for a late single.** It makes the output depend on timing in the PC.
  Count it and drop it.
:::

## Windows: fixed or per single

### Two definitions of "close enough"

There are two common ways to open windows, and they give different answers for the same
stream.

In a **fixed window**, the first single that is not yet in a window opens one; every
single up to τ later joins it; the window closes, and the next window opens at the first
single after it. Every single belongs to exactly one window. The window does not extend
when a single falls into it, so it is non-paralyzable in the sense of Chapter 11.

In a **per-single window**, every single opens its own window and is paired with the
singles up to τ after it. A single can then be part of several windows: its own, and those
of the singles up to τ before it.

The GATE simulation toolkit offers both, and its documentation describes the same
distinction (verify: the GATE version in use, where the options are named in the
coincidence sorter's settings). Hardware sorters often implement the fixed window, because
it maps to a simple state machine; software sorters can do either.

### A worked timeline

Take a window of 4 ns and singles at 0, 2.5, 3.5, 6, 12 and 14.5 ns, all inside the energy
window (the left half of the figure).

**Fixed.** The single at 0 opens [0, 4]. It holds 0, 2.5 and 3.5: three singles, a
multiple. The next single, 6, opens [6, 10]: alone. 12 opens [12, 16] with 14.5: a pair.
One pair, one multiple, one single alone.

**Per single.** 0 opens [0, 4] with 2.5 and 3.5: a multiple. 2.5 opens [2.5, 6.5] with 3.5
and 6: another multiple. 3.5 opens [3.5, 7.5] with 6: a pair, (3.5, 6), that the fixed
window never sees. 6 is alone, 12 and 14.5 are a pair again, 14.5 is alone. Two pairs and
two multiples.

![Fixed and per-single windows on the same singles (4 ns window). Red windows hold three or more singles, blue exactly two, gray one. The bottom row shows the delayed windows of the fixed openers, shortened to D = 20 ns for the figure.](src/img/ch10-windows.png){width=100%}

The per-single sorter found a pair that the fixed one did not, but look at that pair: the
single at 3.5 ns was also in a multiple with the singles at 0 and 2.5. If those three came
from two decays, the pair (3.5, 6) is at least as likely to be a random as a true. Per-single
windows find more pairs at high rates, and more of what they add are randoms. Fixed windows
are simpler to reason about: every single is in one window, and the counts of windows with
one, two and three or more singles add up to the number of singles. MiniDAQ uses fixed
windows by default and offers per-single windows as an option.

One subtlety makes per-single windows easy to get wrong. If every window resolves all the
pairs among its singles, the pair (3.5, 6) is a pair of the window opened at 2.5 and again
of the window opened at 3.5, and a policy that keeps every good pair keeps it twice. In
MiniDAQ, a per-single window's candidate pairs are those that contain its opener, so each
pair is considered once, in the window of its earlier single. (The first version of the
sorter had this bug; a unit test with three singles 1 ns apart now pins it down.)

### Multiples

A window with three or more singles is a **multiple**. With three singles there are three
possible pairs, and at most one of them is a true, because one annihilation makes at most
two photons. The other singles came from other decays: the window holds at least one
random pair, usually two. The sorter must decide what to do, and the GATE documentation
lists the common policies (verify: names and the full list in the GATE version in use;
GATE has more variants than the four here):

- **Kill all**: discard the whole window. Simple, and it loses the true pair that some
  multiples contain.
- **Take all goods**: keep every pair in the window that passes the geometry gate. It keeps
  the true, and all the random pairs that happen to be good.
- **Take the winner of goods**: keep the good pair with the highest summed energy. A
  photon that scattered has lost energy, so the highest-energy pair is more likely to be the
  true. MiniDAQ breaks ties by keeping the earlier pair, which makes the result
  deterministic.
- **Keep if only one good**: keep the window's good pair if exactly one pair is good,
  otherwise discard the window. Without a geometry cut every pair is good, a window of three
  has three good pairs and never exactly one, and this policy behaves exactly like kill all.

How often do multiples occur? For a single in a window of width τ, with an uncorrelated
singles rate S, the chance that another single falls into the window is about Sτ. At
20 MBq the simulator gives 4.0 M singles per second inside the energy window; with
τ = 4 ns, Sτ = 0.016. A window that already holds a true pair gains a third single with
roughly that probability, so about one or two percent of them become multiples, and since
both the pairs and the chance grow with the activity, the number of multiples grows with
its square. The measured counts agree:
16 multiples per second at 1 MBq, 7,180 at 20 MBq and 29,000 at 40 MBq
(`measurements/ch10/validation.txt`).

What each policy does to the result is measured below, after the geometry gate, because
"good" depends on it.

::: box-mistakes
- **Calling a window of two "a coincidence" before the geometry gate.** A window of two can
  hold a pair that is not good. MiniDAQ counts it in `geometry_rejected` and keeps the
  window's accounting unchanged.
- **A policy that is not deterministic.** "The winner" needs a tie rule, and the rule must
  not depend on memory addresses or hash order. Two runs on the same data must give the
  same pairs.
- **Per-single windows that resolve every pair in every window.** They count some pairs
  twice. Pair the opener with the later singles only.
:::

## Geometry acceptance

### Sectors

A photon pair from inside the field of view hits two crystals far apart around the ring.
Two crystals in the same module, or in modules next to each other, can only be hit together
by an annihilation near the detector itself, outside the field of view, or by one photon
that scattered from one crystal into its neighbor (inter-crystal scatter, Chapter 8). The
**minimum sector difference** rejects such pairs: the ring is divided into sectors, and a
pair is good only if its two sectors are at least that many apart, counted the short way
around the ring.

MiniDAQ's model scanner has 24 blocks around the ring, each 16 crystals wide, 384 crystals
per ring, and the sectors are the blocks. A minimum difference of 1 rejects pairs within
one block; 2 also rejects pairs in neighboring blocks. The distance between sectors s~a~
and s~b~ is min(|s~a~ − s~b~|, 24 − |s~a~ − s~b~|), so blocks 0 and 23 are neighbors. The
configuration accepts at most 12, half the ring. (assumption: confirm with team how the
your scanner's sectors are defined; a brain scanner may group modules differently, and the
axial direction can have its own rule.)

### Field of view

The second gate asks whether the line of response passes through the field of view, a
cylinder of radius r around the scanner's axis. In the transaxial plane, the distance from
the axis to the line through the crystal faces p and q is |p × q| / |q − p|, the
cross-product formula for the distance from the origin to a line. A pair is good if that
distance is at most r.

**Worked example.** The crystal faces sit on a circle of radius R = 150 mm. Two crystals
96 positions apart are a quarter of the ring apart, 90°. The chord between them is at a
distance R cos(45°) = 106.1 mm from the axis, so the pair passes a 120 mm field-of-view cut.
For two crystals Δ positions apart, the distance is R cos(πΔ/384), and it falls below
120 mm when cos(πΔ/384) ≤ 0.8, at Δ ≥ 79. A 120 mm cut therefore rejects every pair less
than 79 crystals apart, almost five blocks: stronger than any sector cut you would set. A
pair 192 positions apart, exactly opposite, passes through the axis.

MiniDAQ evaluates the cut without a square root and without a division: it compares
(p × q)² with r² |q − p|², and takes the crystal positions from the compile-time table of
Chapter 1 rather than computing cosines:

```{.cpp include="minidaq/src/processing/coincidence_sorter.cpp" snippet="good"}
```

Two crystals at the same transaxial position, in different rings, have no transaxial line
at all (|q − p| = 0); the function rejects them, which a real scanner would decide with the
axial geometry (verify: how your scanner's sorter treats pairs in the same transaxial
position).

## What the policy does: measurements

With the gates defined, the policies can be compared on the simulator's data, where the
ground truth says which pair is a true, a scatter or a random. The script
`measurements/ch10/validation.py` runs `minidaq_sim` from 1 to 40 MBq with each policy, the
same singles for every policy at one activity, a 4 ns fixed window, the 435 to 585 keV
window and a delayed window at 100 ns. The table below (delayed error: delayed count against
the true randoms, with one standard deviation) is from the run with the sector cut
at 1 and a 120 mm field of view; the file also has the run without cuts.

| MBq | Policy | Trues/s | Randoms/s | Randoms in prompts | Delayed error |
|----:|:------------------|----------:|----------:|---------:|--------------:|
| 5 | kill all | 47,198 | 1,782 | 2.7% | +11.6 ± 5.4% |
| 5 | take all goods | 47,498 | 2,330 | 3.5% | −3.1 ± 4.6% |
| 20 | kill all | 184,820 | 28,740 | 10.3% | +7.1 ± 2.7% |
| 20 | take all goods | 189,890 | 37,840 | 12.8% | −5.8 ± 2.3% |
| 20 | winner of goods | 187,290 | 32,790 | 11.4% | +6.1 ± 2.5% |
| 20 | only one good | 184,890 | 28,770 | 10.3% | +17.9 ± 2.8% |
| 40 | kill all | 358,920 | 111,880 | 18.6% | +5.0 ± 1.9% |
| 40 | take all goods | 379,260 | 149,880 | 22.5% | −8.1 ± 1.6% |
| 40 | winner of goods | 368,660 | 128,680 | 20.4% | +3.9 ± 1.8% |
| 40 | only one good | 359,120 | 112,040 | 18.6% | +15.6 ± 2.0% |

![Randoms fraction of the prompts, and the error of the delayed-window estimate, against activity, for the four policies (sector cut 1, 120 mm field of view; error bars are one standard deviation of counting statistics).](src/img/ch10-policies.png){width=100%}

Three things stand out.

**At low activity the policy does not matter.** At 1 MBq there are 16 multiples per second
against 9,400 trues, and the policies differ by less than the counting noise.

**At high activity the policy trades trues for randoms.** At 40 MBq, take all goods finds
20,000 more trues per second than kill all, 5.7% more, and 38,000 more randoms. Most of
what it recovers from multiples is randoms, because a window of three holds at most one
true pair. The winner of goods sits between the two. Whether the extra trues are worth the
extra randoms depends on the noise they add after randoms correction, which is a question
for the image (Chapter 11 introduces the noise-equivalent count rate that answers it).

**The delayed-window estimate depends on the policy.** This is the subject of the next
section, and the reason the policy must be recorded with the data.

## Randoms

### Why randoms can be estimated

A random is a pair of two uncorrelated singles. Their rate depends only on the singles
rates and the window, so it can be estimated from the data without knowing which prompts
are randoms. There are two common estimates.

### The singles-rate estimate

Take two detectors with singles rates S~1~ and S~2~. A single in detector 1 at time t makes
a pair with any single in detector 2 between t − τ and t + τ, an interval of 2τ. The
expected number of such singles is 2τS~2~, and detector 1 has S~1~ singles per second, so
the rate of random pairs is

R~12~ = 2τ S~1~ S~2~.

The factor 2 is easy to lose. A sorter opens its window only after the earlier single, so
it looks like a window of length τ, but either detector can fire first: the pairs where
detector 2 fired first are found from the other side. Exercise 10.6 derives the formula,
checks it on simulated streams, and has a starter with exactly this mistake, made twice so
that the two halves agree with each other and are both wrong.

For a whole scanner, summing over pairs of crystals and dividing by two for the double
count gives about τS² for a total singles rate S. At 20 MBq, S = 4.0 M/s and τ = 4 ns give
64,000 randoms per second, against 63,200 measured with take all goods and no geometry
cut. The estimate needs the singles rate per crystal, which the DAQ counts anyway, and its
statistical noise is small because singles are many. Its weakness is that the singles
include the singles of trues, and that dead time and multiples policies change what the
sorter actually keeps; Oliver and Rafecas compare corrected forms of this estimate that use
both the singles and the prompts (verify: the exact method and the conditions under which
they found it accurate, in their 2016 paper).

### The delayed window

The other estimate measures randoms directly. Each window's opener also opens a second
window of the same width, delayed by D, much longer than any correlation in the data: in
MiniDAQ D = 100 ns, 25 times the window. No single in the delayed window can come from the
same annihilation as the opener, so every pair found there is a random, and the delayed
rate estimates the prompt randoms rate: same opener, same width, same rules, only without
the true partner.

In MiniDAQ the delayed window is [t + D, t + D + τ], inclusive at both ends like the
prompt window. Its pairs are (opener, delayed single), and the multiples policy applies to
them as well: one delayed single is a pair, two or more are a delayed multiple. Delayed
coincidences go to the output with `CoincidenceKind::delayed`.

### Why the estimate depends on the policy

If the delayed window counts randoms "the same way" as the prompt window, why did the
measurement show errors of +5% with kill all and −8% with take all goods at 40 MBq?

Because the delayed window does not see what the prompt window held. Take an opener whose
prompt window holds a true partner and one random single: a multiple. With kill all, the
prompt window is discarded, and the random it contained is lost from the prompts. The
delayed window of the same opener knows nothing about that and counts a random as usual.
The delayed estimate is too high. With take all goods, the same multiple contributes the
true and up to two random pairs to the prompts, while the delayed window, with one single
in it, contributes one. The estimate is too low. With the winner of goods, the true usually
wins and the random is dropped, as with kill all: the estimate is high, slightly less so.
Keep if only one good reads highest with the field-of-view cut, for a different reason:
the multiples it keeps in the prompts mostly yield the true pair, which adds no randoms,
while delayed windows with two singles of which one is good now count a random. At 40 MBq
its delayed count is 10% above kill all's, while its true randoms are only 0.1% above.

The unit test `TheDelayedWindowEstimateDependsOnTheMultiplesPolicy` (SRS-SRT-011) turns
this into a requirement: at 40 MBq, kill all must read high and take all goods low, and
their difference must exceed four standard deviations. It is a test of the physics of the
sorter, not of a number: if a change to the sorter made the two biases equal, something
other than the policy would have changed.

The practical consequence is that a randoms correction must model the policy it was
measured with, or use a policy and an estimator that match. This is one of the questions to
ask the team: which estimator your scanner's reconstruction uses, and whether its bias at
the clinical activity has been measured.

::: box-mistakes
- **R = τS~1~S~2~.** The window is open on both sides of a single for the purpose of
  counting randoms. The rate is 2τS~1~S~2~.
- **A delay that is too short.** If the delay is comparable with the time spread of the
  prompt pairs, or with any periodic structure in the data, the delayed window contains
  correlated pairs. Choose a delay well beyond both and check the delayed time spectrum for
  structure.
- **Assuming the delayed estimate is unbiased.** It is unbiased only for the pairs it
  imitates; with multiples it depends on the policy, by several percent at high activity.
:::

## Merging the boards

### The problem

The sorter needs one stream in time order. A scanner delivers many: one per readout board,
each in order by itself, but not in step with the others. One board's packet for the next
microsecond can arrive before another board's packet for this one, because their links,
buffers and packet sizes differ. Merging the streams is the first stage of sorting, and
the chapter's second question is about it: what breaks if data from one board arrives 10 µs
late?

### A k-way merge with a watermark

Merging k sorted streams is a classic problem (Knuth, volume 3): keep the head of each
stream in a min-heap, take the smallest, replace it by the next single of the same stream.
Each single costs one heap operation, O(log k).

A streaming merger adds one question: when is it safe to release a single? Only when no
board can still send an earlier one. Each board's stream is in order, so once a board has
sent a single at time t, it will not send anything earlier. The merger therefore keeps, for
each board, the latest time it has reported, and computes the **watermark**:

watermark = min over boards of (latest time reported by the board).

Every single earlier than the watermark is safe to release. The idea and the name come from
stream processing systems, where the same problem appears with events from many sources
(Akidau et al., the Dataflow Model). Two refinements make it work for a DAQ.

**Time markers.** A board that sees no photons for a while sends no singles, and its
latest reported time stops. The watermark stops with it, and the merger holds everything.
Readout firmware sends periodic time markers (or empty packets with a time stamp) for this
reason, and MiniDAQ's merger accepts them with `advance(board, t)`: a promise that nothing
earlier than t will follow. (assumption: confirm with team whether your scanner's readout
sends time markers, and how often.)

**A bound on the wait.** A board that stops completely, because its link failed, would hold
the whole scanner back forever. `max_skew` bounds the wait: the watermark never lags the
most advanced board by more than `max_skew`, 100 µs by default. A single that arrives after
its time has been released is late: the merger counts it in `late` and drops it, because
the sorter has already closed the windows it belonged to. `skew_releases` counts the drains
in which the bound, rather than the slowest board, set the watermark, so an operator can
see that a board is lagging before its data is lost.

```{.cpp include="minidaq/src/processing/stream_merger.cpp" snippet="watermark"}
```

Releasing is the heap merge, limited by the watermark:

```{.cpp include="minidaq/src/processing/stream_merger.cpp" snippet="release"}
```

**Ties.** Two boards can report singles with the same time stamp. The output must not
depend on the order in which packets arrived, or two runs on the same data would differ.
The merger orders equal times by MiniDAQ's `TimeOrder` (time, then crystal, the order of
the pipeline's sort stage), then by board number, and singles from one board that are equal
in both keep that board's order. The unit test `TiesComeOutInADeterministicOrder`
(SRS-MRG-005) checks this.

### The 10 µs late board

Now the second question. A board's data arrives 10 µs after the others' data for the same
time.

**With a merger that may wait 100 µs**, nothing is lost. The watermark follows the late
board, the merger holds about 10 µs of everyone else's singles, and the coincidences come
out 10 µs later than they otherwise would. At 8 M singles per second in total that is
about 80 singles of buffer: nothing. The cost is latency, and latency is cheap here.

**With a bound shorter than the delay**, say 5 µs, the watermark runs ahead of the late
board, and almost all of that board's singles arrive after their time was released: they
are counted as late and dropped. The test `ASlowBoardLosesOnlyItsLateSingles`
(SRS-MRG-003) builds exactly this case, with 90 singles from the late board: more than 80
are counted late, the output is still in order, and every single is either delivered or
counted.

**Without a merger**, feeding the sorter in arrival order, the late board's singles are out
of order with respect to the others. The sorter counts each one in `out_of_order` and drops
it, or, in a sorter without that check, pairs them with whatever happens to be near in
arrival order. Either way, every coincidence that involves that board's crystals is lost or
wrong.

The consequence for the image is specific: the lost coincidences all involve one board, so
the lines of response through one region of the ring are missing. In a sinogram this is a
set of diagonal bands, and in the image an artifact, not merely a lower count. A global
count of "coincidences per second" hides the cause; a per-board count of singles and
coincidences shows it at once. This is why MiniDAQ counts late and out-of-order singles
instead of dropping them silently, and why the counters go into the status report.

### Merging by time slices

The heap is not the only design. A **slice merger** takes every board's singles in the
interval [T, T + Δ), sorts them together with a stable sort, emits them, and moves on to
the next interval. Its work per single is a share of a sort over a small array, which
caches well; a heap operation per single over 72 boards touches more memory and branches
unpredictably. Exercise 10.5 implements it, makes its output identical to the heap's
(half-open slices, a stable sort, boards gathered in order) and measures the two on 0.1 s of
simulated 20 MBq data split by block (`measurements/ch10/bench_slice_merge.txt`, medians of
five repetitions on the book's VM):

| Boards | Heap merger | Slice merger |
|---:|---:|---:|
| 4 | 30.4 M singles/s | 48.4 M singles/s |
| 24 | 13.3 M singles/s | 28.4 M singles/s |
| 72 | 10.1 M singles/s | 20.6 M singles/s |

The slices are about twice as fast for many boards. They cost latency: a slice can only be
emitted when every board has reported past its end, so the latency is the watermark's plus
up to Δ. For a DAQ that writes list-mode data, a millisecond of latency is irrelevant, and
the slice merger is the better choice at high board counts. MiniDAQ's library keeps the heap
merger, whose behavior is easier to specify single by single, and records the comparison in
ADR 0010; a team with 72 boards and a throughput problem should switch.

The numbers also say where the pipeline's limit is. The merger handles 14 M singles per
second for 24 boards in `measurements/ch10/bench_sorter.txt`, counting every single before
the energy gate; the sorter handles 68 M. Making the sorter faster changes nothing end to
end until the merger is faster.

::: box-mistakes
- **A watermark that ignores silent boards.** Taking the minimum over boards that have sent
  something releases singles that a board which has not yet spoken could still precede.
  MiniDAQ releases nothing until every board has reported once.
- **No bound on the wait.** One dead link stops the scanner, and the first symptom is
  memory growth. Bound it, count what the bound costs, and alarm on it.
- **Unstable tie order.** `std::sort` does not keep the order of equal elements; use
  `std::stable_sort` or make the comparison total.
:::

## MiniDAQ's sorter

### The design

The sorter is a class with two operations, `push` and `flush`, and a set of counters.
`push` takes singles in time order, in chunks of any size, and appends the coincidences that
those singles complete; `flush` closes every open window at the end of a run. Its
configuration is a value type, checked by `validate` before the sorter exists:

```{.cpp include="minidaq/include/minidaq/processing/coincidence_sorter.hpp" snippet="config"}
```

The constraints are those of the earlier sections: a window in (0, 1 µs], a delay of zero
(off) or more than the window and at most 1 ms, a finite energy window with low ≤ high
(written so that NaN fails every check), a sector difference of at most 12, and a field of
view smaller than the ring. A configuration that fails throws from the constructor, so a
pipeline with a bad sorter configuration never starts.

### One pass, one buffer

The sorter holds the accepted singles in a vector and three indices: the oldest single still
needed (`first_`), the next single to open a window (`opener_`) and the first single that
can be in the next delayed window (`delayed_begin_`). Each incoming single goes through the
energy gate and the order check, then closes every window that it proves complete, then
joins the buffer:

```{.cpp include="minidaq/src/processing/coincidence_sorter.cpp" snippet="push"}
```

A window opened at t is complete when a single later than t + horizon arrives, where the
horizon is the window, or the delay plus the window when the delayed window is on. Closing a
window finds its end by scanning forward from the opener, resolves the prompts, finds the
delayed window by scanning forward from where the last one started (it only moves forward),
and moves the opener:

```{.cpp include="minidaq/src/processing/coincidence_sorter.cpp" snippet="close"}
```

No window is copied anywhere. A window is an index range into the buffer, and resolving it
reads the singles in place. Once enough of the buffer is behind `first_`, one `erase` moves
the rest to the front: amortized, each single is moved a small constant number of times,
and the buffer holds about one horizon of data, 104 ns, a handful of singles at any
realistic rate.

The multiples policies are one loop over the candidate pairs, with the policy deciding what
to keep:

```{.cpp include="minidaq/src/processing/coincidence_sorter.cpp" snippet="resolve"}
```

### Chunking does not matter

A window closes only when a later single proves it complete, never because a chunk ended.
The output is therefore a function of the singles alone: one chunk of a million singles,
a million chunks of one, or anything between give the same coincidences in the same order.
This property is what makes the sorter testable against a reference, lets the pipeline feed
it batches of any size, and lets Exercise 10.3 split the work across threads. It is tested
directly (`ChunkingDoesNotChangeTheResult`, SRS-SRT-008, with random chunk sizes) and by the
fuzzer on every input.

### Every single is accounted for

The counters follow the same rule as Chapter 9's link counters: everything that enters is
accounted for somewhere.

```{.cpp include="minidaq/include/minidaq/processing/coincidence_sorter.hpp" snippet="stats"}
```

In fixed mode the identity singles_in = energy_rejected + out_of_order + singles_alone +
2 × pair_windows + singles_in_multiples holds exactly, after `flush`. The test
`EverySingleIsAccountedFor` (SRS-SRT-009) checks it on simulated data, and the fuzzer checks
it on every input. A sorter whose counters do not add up has a bug, even if its coincidences
look right.

### In the pipeline

The sorter replaces the placeholder pair stage of Chapter 3. The pipeline's configuration
now holds a `SorterConfig`; the pipeline creates the sorter in its constructor, so a bad
configuration throws there rather than in a running thread. The pair stage pushes each
batch of singles into the sorter and copies what it found into output batches:

```{.cpp include="minidaq/src/pipeline/acquisition_pipeline.cpp" snippet="pair"}
```

Two details deserve a comment. First, a sorter holds singles back until their windows
complete, so a coincidence can come out one batch after the singles that made it. The
latency histogram of Chapter 4 measures from the time a batch entered the pipeline, and a
coincidence must carry the origin of the batch its first single came from, not of the batch
that happened to complete it. The pair stage keeps a small ring of recent batches, keyed by
the time of their last single, and looks the origin up (`OriginTrack`). Second, the
sorter's counters are copied into atomics after every batch, so the status report can read
them from another thread while the stage runs. Two `static_assert`s check that the list of
copied fields has one entry per field and that the structure holds nothing else, so a
counter added later cannot be forgotten.

The acquisition service's status report gains a `"sorter"` object with all eleven counters.
Singles that the sorter drops before windowing (energy and order) are counted as the
stage's `items_filtered`, so the stage's conservation check from Chapter 3 still holds.

### The configuration, version 1.2

The configuration file gains a `sorter` object, and the schema version becomes 1.2: a
minor version, because every 1.0 and 1.1 file is still valid. It does not run quite as
before, and the changelog says so: the placeholder pair stage of earlier versions had no
energy gate and no delayed window, and a file without a `sorter` object now gets the
sorter's defaults, which include both. The format is compatible; the pipeline's behavior
changed, as it was meant to.

```json
"sorter": {
  "delay_ps": 100000,
  "mode": "fixed",
  "multiples": "take_winner_of_goods",
  "energy_low_kev": 435.0,
  "energy_high_kev": 585.0,
  "min_sector_difference": 1,
  "fov_radius_mm": 120.0
}
```

The window itself stays `/pipeline/coincidence_window_ps`, as in 1.0. Two rules involve two
values, and the reader reports them at the value a user would change: a delay that is not
more than the window is reported at `/sorter/delay_ps`, and an energy window with low above
high at `/sorter/energy_low_kev`. The JSON Schema document in
`docs/architecture/acquisition-config.schema.json` describes the new object, and the
configuration test that walks the schema checks that every property the schema names is
read and written.

## Validation

### Against the ground truth

Chapter 8's simulator records, for every single, the decay it came from and whether its
photon scattered, and its truth counter classifies the pairs of a simple fixed-window
sorter. Configured with the same rules (fixed window, kill all, no geometry cut), MiniDAQ's
sorter must find exactly the same prompts and multiples: not within 0.5%, exactly. The test
`MatchesTheSimulatorsGroundTruth` (SRS-SRT-010) runs 50 ms at 5 MBq and compares the
counts. A tolerance of 0.5% may look like a reasonable target. With identical rules there
is no reason for any difference, and a tolerance would hide a bug that loses one pair in a
thousand. Exercise 10.1 asks you to write the reference sorter and holds it to the same
standard.

`minidaq_sim` classifies every coincidence the sorter finds by looking its two singles up in
the truth, so you can see the trues, scatters and randoms for any configuration:

```
build/release/minidaq/apps/minidaq_sim --activity 20e6 --seconds 0.1 \
    --policy take_winner_of_goods --sectors 1 --fov 120
```

### By fuzzing

The fuzz target `fuzz/fuzz_sorter.cpp` builds a configuration and a stream of singles from
the fuzzer's bytes: any mode, policy, window from 0.1 to 25.6 ns, delayed window on or off,
cuts on or off, and singles with steps of 0 to 12.75 ns, so ties are common. For every input
it checks that the output and the counters do not depend on where the input is split, that
the counters add up, that every prompt is within the window and every delayed pair within
[D, D + τ], that every pair passes the geometry gate, and that the merger, given the same
singles spread over up to eight boards in uneven chunks, gives back exactly the input
times in order with nothing late. A ten-minute campaign on the book's VM ran 3,874,747
inputs, about 6,400 per second, with no failure; coverage grew from 282 to 313 edges and
found nothing new after the first 846,000 inputs (`measurements/ch10/fuzz_sorter.txt`).
The campaign runs again whenever the sorter changes.

## Throughput

### The target

How fast must the sorter be? A clinical PET scanner can produce tens of millions of singles
per second at high activity (verify: your scanner's expected peak singles rate, which
depends on its geometry and the activities used). This chapter sets a target of
30 M singles per second on one core, with bounded latency, and the measurements are taken
against it. As always, the target comes from the system, and Chapter 11's count-rate curves
are where the real number is derived.

### The measurements

`benchmarks/bm_sorter.cpp` sorts 0.2 s of simulated 20 MBq singles, pushed in batches of
4,096 as in the pipeline. It counts every single offered, including the 55% that the energy
gate rejects (`measurements/ch10/bench_sorter.txt`, means of five repetitions on the book's
VM, GCC 13.3, `-O2`):

| Configuration | Singles offered per second |
|:---|---:|
| Fixed windows, kill all, no delayed window | 89.1 M |
| Fixed windows, any policy, delayed window | 68.2 to 68.9 M |
| Fixed windows, kill all, delayed window, 120 mm field of view | 68.4 M |
| Per-single windows, kill all, delayed window | 67.3 M |

At 68 M singles offered per second, 31 M per second pass the energy window: the target is
met with the delayed window on, with no margin to spare in the singles that matter. The
policy hardly changes the cost, because multiples are rare; the delayed window costs about
a quarter, because it adds a second scan per window. The field-of-view cut costs nothing
measurable once it is a few multiplications on table values.

The latency is bounded by the data: a window closes as soon as the first single beyond its
horizon arrives, and the horizon is 104 ns. At the end of a batch, the singles of the last
104 ns wait for the next batch, which the source publishes after at most
`max_batch_delay_us` even at low rates. If the data stops altogether, they wait for the end
of the run, when `flush` closes every window; a sorter that must report coincidences while
the detector is silent would need a time marker from the source, as the merger has.

### Where the time goes in a naive sorter

Exercise 10.4 gives you a correct and slow sorter, written the obvious way, and asks you to
make it at least twice as fast without changing a single coincidence. Its profile is
instructive: 53% of the time is spent indexing a `std::deque` while scanning windows, 27% in
`malloc` and `free` for two vectors built for every window, and 12% in `sincos` for the
crystal positions of every pair. The `std::function` called for every coincidence, which
many people would suspect first, costs 0.5%. The solution reaches 41 M singles per second
inside the energy window, 2.5 times the baseline. (The exercise measures differently, best
of seven interleaved runs and only the singles inside the energy window, and its sorter keeps no
counters; do not compare its numbers with the table above.) Profile first.

### Parallel sorting by time slices

When one core is not enough, the stream can be cut into time slices sorted on separate
threads. The hard part is the boundaries. In fixed mode, which singles open windows depends
on the history: cut in the middle of a run of singles closer than τ, and the second slice
opens windows that the serial sorter never opened.

The history stops mattering at a gap. If two consecutive accepted singles are more than τ
apart, the window that holds the first cannot hold the second, so the second opens a new
window whatever came before. A slice that starts there is sorted exactly as the serial
sorter would sort it. The cut rule is therefore: take the first gap wider than τ, between
singles that pass the energy window, after each nominal boundary.

The delayed window adds the second half of the problem. An opener near the end of a slice
has its delayed window in the next slice. So each worker reads ahead by D + τ beyond its
end, sorts those singles too, and then drops every coincidence whose opener is at or after
the next slice's first single: those belong to the next worker, which finds them itself.
Exercise 10.3 implements this and asks for the proof that no coincidence is lost or
doubled. Its starter, which cuts at equal sizes, passes a test on realistic data, because at
170 ns between singles a 4 ns window rarely straddles a cut; the exercise's other tests
build exactly the cases that break it. That is a lesson in itself: a boundary bug that
loses one pair in a hundred thousand passes every count-based test.

When the stream has no gaps, at very high rates or with a wide window, there is nowhere to
cut and the slices stay on one thread. Per-single windows have no history, and any cut works
with the same read-ahead.

## Hardware or software sorting

Where the sorter runs is an architectural decision with consequences for everything else.

**Sorting in hardware**, in FPGAs on the detector side, is the traditional design for
clinical scanners. Singles are paired close to the detector, and only coincidences travel to
the PC, which reduces the data rate by roughly the ratio of singles to coincidences, a
factor of 10 to 30 at the rates in this chapter. The logic is fast and its latency is fixed.
The costs are flexibility and visibility: changing a policy or a window means new firmware,
with its own verification, and the singles are gone, so a question about the sorter cannot
be answered from the data afterwards.

**Sorting in software** receives all singles. The link must carry them, which Chapter 9
sized: 14.8 M singles per second per Gigabit link in MDQ-R1 packets. In exchange, the
sorter is ordinary C++, testable against a simulator, changeable in a release, and
the singles can be recorded so that the same acquisition can be sorted again with other
rules. Research systems and several newer designs take this route; whether your scanner's
sorter is in firmware, in software, or split between them is the first thing to find out
(assumption: confirm with team).

**Hybrid designs** are common: a coarse coincidence trigger in hardware to reduce the
rate, and the final sorting, with policies and delayed windows, in software. Whatever the
split, the questions of this chapter apply to the part you own: which rules, documented
where, verified how, and what the counters say when the rules discard data.

::: box-mistakes
- **A sorter that only runs in the full system.** If the sorter is not a library that can
  be fed a recorded or simulated stream, it cannot be tested against ground truth. Keep it
  separable from its transport.
- **Throughput measured with everything inside the energy window.** Real streams have half
  or more of their singles outside it; say which singles your rate counts.
- **Equal-size slices for a parallel sorter.** They pass realistic tests and lose
  coincidences at the boundaries. Cut at gaps.
:::

::: box-regulated
The sorter turns detector data into the counts a clinical image is made from, so its
behavior is part of the device's intended performance.

- **Every rule is a requirement.** The window, its boundary, the energy and geometry gates,
  each multiples policy, the delayed window and the accounting identity are software
  requirements with tests (SRS-SRT-001 to 011 and SRS-MRG-001 to 005 in MiniDAQ). A change
  to a policy or a default is a change to the device's performance, with the verification
  and the risk analysis that implies (IEC 62304 change control, Chapter 14).
- **The configuration belongs to the data.** The policy, the window, the gates and the
  delay must be recorded with every acquisition (the list-mode header of Chapter 12), because
  the randoms correction and any later analysis depend on them.
- **Validation against a simulator is evidence only if the simulator is fit for it.**
  The ground truth comes from a tool, and the argument that the tool is right for the
  purpose belongs in the verification records (verify: your quality system's procedure for
  validating software tools, for example under ISO 13485 clause 4.1.6 for software used in
  the quality system).
- **Counters are risk controls.** Late, out-of-order and energy-rejected singles are
  counted, reported and, above a threshold, can fault a run. Whether lost coincidences can
  affect a clinical result is a hazard for the risk file (ISO 14971, Chapter 15).
:::

::: box-askteam
1. Where does your scanner sort coincidences: in firmware, in software, or both? Which
   rules does each part apply, and where are they specified?
2. Which window, energy window, multiples policy and geometry cuts are used for clinical
   acquisitions, and who decided them, on what evidence?
3. How are randoms estimated (delayed window, singles rates, a combination), and has the
   estimator's bias at clinical activities been measured against simulation or phantoms?
4. How many readout boards send data to the PC, do they send time markers, and how far out
   of step can their streams be? What happens today when one board falls behind?
5. What is the peak singles rate the sorter must handle, and what is the current margin?
:::

## Exercises {.unnumbered}

**Exercise 10.1 (M): A reference sorter, checked against the truth.** *Goal:* the
simplest correct sorter (fixed windows, multiples discarded, an energy window), returning
coincidences as indices into the input so that each can be classified as a true, a scatter
or a random from the simulator's truth. *Starter:* `exercises/ch10/e1_reference_sorter/`
(pairs each single with the next one if it is close enough; no energy window; a third single
forms another pair; everything is a true). *Acceptance:* `tests/test_reference_sorter.cpp`
passes: an inclusive window, nothing from a window of three, the next window opened by the
single after a window, no part for a single outside the energy window; at 10 MBq for 50 ms,
trues, scatters and randoms equal to the Chapter 8 truth counter exactly, and pairs exactly
those of MiniDAQ's `CoincidenceSorter`. The test asks for exact agreement, not "within
0.5%", and the README explains why. *Time:* 2 hours.

**Exercise 10.2 (M): Multiples policies.** *Goal:* implement the four policies as one
function that resolves one window, then measure what each does to the trues and randoms from
1 to 40 MBq and choose one for a brain scanner in one paragraph. *Starter:*
`exercises/ch10/e2_multiples_policies/` (kill all is right; every other policy keeps every
pair without checking that it is good; `driver.cpp` is provided). *Acceptance:*
`tests/test_policies.cpp` passes: one window by hand for each policy, the energy winner, the
tie rule and the case with no good pair; on 5 and 30 MBq data with a sector cut and a 120 mm
field of view, exactly the coincidences of `CoincidenceSorter` for every policy; the policies
ordered by what they keep. Then plot trues per second and the randoms fraction against
activity, one line per policy, from `minidaq_sim` or `measurements/ch10/validation.txt`.
*Time:* 2.5 hours.

**Exercise 10.3 (H): A parallel sorter that loses and doubles nothing.** *Goal:* split a
time-ordered stream into slices, sort each on its own thread with `CoincidenceSorter`, join
the results into exactly the serial result, and write down why the cut rule is correct.
*Starter:* `exercises/ch10/e3_parallel_slices/` (equal-size pieces sorted separately).
*Acceptance:* `tests/test_parallel_sorter.cpp` passes: on 10 ms at 30 MBq, with kill all and
take all goods, 1, 2, 3, 4 and 7 threads give the serial result, delayed coincidences
included; on a dense synthetic stream with rejected singles between accepted ones, 4 threads
give the serial result and every cut falls at a gap wider than the window between accepted
singles; a pair straddling the nominal middle with a delayed partner in the second half is
found once. Half a page: the rule, why it is correct, and what happens without gaps.
*Time:* 4 hours.

**Exercise 10.4 (H): Reach the throughput target.** *Goal:* make a correct, slow sorter at
least twice as fast and fast enough for 30 M singles per second inside the energy window on
one core, without changing a single coincidence, and write a one-page performance report.
*Starter:* `exercises/ch10/e4_fast_sorter/` (a `std::deque`, two vectors per window, a
`std::function` per coincidence, `cos` and `sin` per pair, `std::hypot` and a division for
the field of view). *Acceptance:* `tests/test_fast_sorter.cpp` passes: for all four
policies, with and without the delayed window, with a 120 mm field of view and random
chunks, exactly the coincidences of `CoincidenceSorter`; `FastSorter.FastEnough` (release
builds without sanitizers) measures at least twice the baseline and more than 30 M singles
per second inside the energy window, best of seven interleaved runs (`EX_MIN_SPEEDUP` and
`EX_MIN_SINGLES_PER_S` override the limits when you have measured a reason). The report:
machine, compiler and flags, the profile before with numbers, each change and what it
bought, the result with its spread, what you would try next. *Time:* 4 hours plus the
report.

**Exercise 10.5 (M, extra): Merge by time slices, and measure it against the heap.**
*Goal:* a slice merger whose output is identical to `StreamMerger`'s, ties included, and a
measurement of the two for 4, 24 and 72 boards with a sentence on what each costs in
latency. *Starter:* `exercises/ch10/e5_slice_merge/` (a single on a slice edge is taken
twice, the last partial slice is lost, and `std::sort` reorders equal singles).
*Acceptance:* `tests/test_slice_merge.cpp` passes: for 1, 4, 24 and 72 boards and slices
from 1 ns to 10 µs, with frequent ties and singles on slice edges, exactly the heap merger's
output; singles on the edges, an empty board, a last single alone in its slice. Report the
medians of `ch10_e5_slice_merge_solution_bench --benchmark_repetitions=5`. *Time:* 2 hours.

**Exercise 10.6 (E, extra): Randoms from the singles rates.** *Goal:* derive R = 2τS~1~S~2~
and check it on simulated streams, with independent singles only and with true pairs
added, where it must agree with the delayed-window count. *Starter:*
`exercises/ch10/e6_randoms_estimate/` (Python; τS~1~S~2~, and a counter that only looks for
detector 2 after detector 1). *Acceptance:* `tests/test_randoms.py` passes: 8,000 randoms
per second for 1 M singles per second in each detector and 4 ns; a hand-made case in both
directions; on 0.5 s of Poisson streams at 1 M and 0.8 M per second, prompt and delayed
counts within four standard deviations of 2τS~1~S~2~; with 200,000 true pairs per second
added, prompts minus delayed equal to the trues and the delayed count in agreement with the
singles-based estimate. *Time:* 1 hour.

## MiniDAQ milestone: the coincidence sorter {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ sorts coincidences with a production-quality sorter: fixed or per-single
windows, four multiples policies selected by configuration, energy and geometry gates, a
delayed window, counters that account for every single, a merger for many boards, and a
validation report against the simulator's truth. **Start:** tag `ch09`. **End:** tag `ch10`.
:::

1. Add the sorter, `processing/coincidence_sorter.hpp` and `.cpp` in MiniDAQ's include and
   source trees: `SorterConfig`, `validate`, `SorterStats`, `CoincidenceSorter`, with
   `test_coincidence_sorter.cpp` (SRS-SRT-001 to 011).
2. Add `processing/stream_merger.hpp` and `.cpp`: `MergerConfig`, `MergerStats`,
   `StreamMerger` with watermark, time markers and `max_skew`, with `test_stream_merger.cpp`
   (SRS-MRG-001 to 005).
3. Replace the pipeline's placeholder pair stage with the sorter: `PipelineConfig::sorter`,
   the sorter created in the constructor, origin tracking for latency, the sorter's counters
   in atomics and in the service's status report.
4. Extend the configuration to schema 1.2 with the `sorter` object, the cross-field errors,
   the JSON Schema document and the configuration tests.
5. Give `minidaq_sim` the options `--mode`, `--policy`, `--delay`, `--sectors` and `--fov`
   and a report that classifies every coincidence by truth; add
   `measurements/ch10/validation.py` and its results.
6. Add `benchmarks/bm_sorter.cpp` and the fuzz target `fuzz/fuzz_sorter.cpp` with a seed
   corpus; run a ten-minute campaign and record it.

**Definition of done.** `ci/run_all.sh` is green on all six presets; `tools/static_analysis.sh`
reports nothing; `architecture.layers` passes (the sorter and the merger are in the
core layer's processing module and use nothing outside the core); with the Chapter 8 truth counter's rules, the
sorter finds exactly its prompts; the validation table is regenerated by one command; the
benchmark shows more than 30 M singles per second inside the energy window with the delayed
window on; the fuzz campaign finds nothing in ten minutes. Tag `ch10`.

## Check yourself {.unnumbered}

1. Why must singles be time-sorted before windowing?
2. What breaks if data from one board arrives 10 µs late? Answer for a merger that may wait
   100 µs, one that may wait 5 µs, and no merger at all.
3. Give a stream of four singles on which fixed and per-single windows find different
   pairs.
4. Why does a window of three singles contain at most one true pair, and what does that
   imply for take all goods at high activity?
5. Why does keep if only one good behave exactly like kill all when there is no geometry
   cut?
6. Derive R = 2τS~1~S~2~. Where does the factor 2 come from, given that the sorter opens its
   window only after a single?
7. With kill all, why does the delayed-window estimate read high at 40 MBq?
8. A pair of crystals 96 positions apart on a 150 mm ring: does its line of response pass a
   120 mm field-of-view cut? How far apart must two crystals be to pass?
9. What does the watermark of a merger guarantee, and why must it wait until every board has
   reported at least once?
10. Why is a gap wider than the window between accepted singles a safe place to cut a fixed-
    window stream for parallel sorting, and why must the gap be measured after the energy
    gate?
11. Your sorter's counters do not add up after a run, but the coincidences match the
    reference. What do you conclude?
12. Name two advantages of sorting in software and one of sorting in firmware.

## Summary {.unnumbered}

- A sorter pairs singles in time order within a window τ; it can only work in one pass with
  a bounded buffer because the input is time-ordered, so order first, then sort.
- Fixed windows put each single in one window; per-single windows find more pairs at high
  rates, more of them randoms, and must pair only the opener to avoid double counting.
- Multiples policies trade trues for randoms: at 40 MBq take all goods finds 5.7% more trues
  than kill all and a randoms fraction of 22.5% against 18.6%.
- Geometry gates reject pairs within or near one sector and lines of response outside the
  field of view; compute them from tables, squared, without divisions.
- Randoms: R = 2τS~1~S~2~ from the singles, or a delayed window; the delayed estimate's bias
  depends on the multiples policy, so the policy must travel with the data.
- Many boards need a merger: a k-way merge released by a watermark, with time markers, a
  bound on the wait, and counters for late singles; slices are twice as fast for many boards.
- A late board loses the coincidences of its own crystals: a geometric artifact, visible in
  per-board counters, invisible in a global count.
- Validate exactly against ground truth where the rules are the same, and fuzz for the
  properties: chunking does not matter, the counters add up, every pair obeys the rules.
- MiniDAQ's sorter reaches 31 M singles per second inside the energy window with the delayed
  window on; parallelize at gaps wider than the window, with a read-ahead of D + τ.

## Further reading {.unnumbered}

- J. F. Oliver and M. Rafecas, "Modelling random coincidences in positron emission
  tomography by using singles and prompts: a comparison study", *PLoS ONE* 11(9) (2016)
  e0162096.
- S. Jan et al., "GATE: a simulation toolkit for PET and SPECT", *Physics in Medicine and
  Biology* 49 (2004) 4543–4561; and the GATE user documentation, section on the digitizer's
  coincidence sorter and its multiples policies.
- S. R. Cherry, J. A. Sorenson and M. E. Phelps, *Physics in Nuclear Medicine*, 4th ed.,
  Elsevier Saunders, 2012: the chapters on PET coincidence detection and randoms.
- D. L. Bailey, D. W. Townsend, P. E. Valk and M. N. Maisey (eds.), *Positron Emission
  Tomography: Basic Sciences*, Springer, 2005.
- D. Brasse et al., "Correction methods for random coincidences in fully 3D whole-body PET:
  impact on data and image quality", *Journal of Nuclear Medicine* 46(5) (2005) 859–867
  (verify: the citation details).
- T. Merlin et al., "CASToR: a generic data organization and processing code framework for
  multi-modal and multi-dimensional tomographic reconstruction", *Physics in Medicine and
  Biology* 63 (2018) 185005; and K. Thielemans et al., "STIR: software for tomographic image
  reconstruction release 2", *Physics in Medicine and Biology* 57 (2012) 867–883: their
  documentation describes list-mode conventions for prompts and delayed events.
- D. E. Knuth, *The Art of Computer Programming, Volume 3: Sorting and Searching*, 2nd ed.,
  Addison-Wesley, 1998: merging and priority queues.
- T. Akidau et al., "The Dataflow Model: a practical approach to balancing correctness,
  latency, and cost in massive-scale, unbounded, out-of-order data processing",
  *Proceedings of the VLDB Endowment* 8(12) (2015) 1792–1803: watermarks.
