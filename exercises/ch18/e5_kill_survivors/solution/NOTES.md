# Exercise 18.5: notes on the solution

With MiniDAQ's own tracker tests (the eleven `SequenceTracker` tests and the tracker property), the
tool made 41 mutants of the tracker's template code: 22 were killed, 9 made the tests run past the
time limit (a mutant that loops forever is noticed, so it counts as killed), 3 did not compile, and
7 survived (`measurements/ch18/mutation-tracker-baseline.txt`). None of the seven was equivalent. They
were two gaps:

- **The hold clock** (6 survivors, lines 259, 279, 283 and 300). The tests checked that a gap is
  lost after the hold time, but always with one gap, one held packet, and a clock that started
  near zero. A mutant that restarts the clock with every packet held, one that never restarts it
  when the first gap closes, one that takes the minimum over unused slots, and one that adds the
  start time instead of subtracting it all gave the same answers there. The class comment says
  "the gap has waited max_hold_ns", which pins down all four: three tests with two gaps, two held
  packets, and a start late in the run kill them.
- **The edge of a restart** (1 survivor, line 211). "A jump forward of more than max_gap_packets"
  is a restart; a jump of exactly that many is loss. `AJumpBeyondTheMaximumGapIsARestart` used a
  jump of 2^31, far from the edge. A small `max_gap_packets` makes the edge cheap to test.

How do you tell an equivalent mutant from a gap? Ask for the input that tells the two versions
apart, and write it down. For each survivor here the input took a minute to find once the class
comment was read for what it promises (the hold time per gap, the restart threshold); for an
equivalent mutant no such input exists, and the argument is why: the two branches give the same
value (`a > b ? a - b : b - a` with `>=`), or the difference is only in time or memory, which a unit
test does not observe. Write that argument in `survivors.json`, where a reviewer can check it.

The report records the SHA-256 of the header, so a change to the tracker makes the recorded report
stale and the check fails until the tool is run again. That is on purpose: a mutation report, like
any measurement, is evidence for the code it was made from.
