# Exercise 15.3: notes

**The gap.** Reading the multiples resolution against the code shows that
`take_winner_of_goods` keeps the earlier pair when two good pairs have the same summed energy
(a strict `>` in a loop over pairs in time order). Nothing required it and no test checked it,
so an optimization that reordered the loop would have changed the coincidences of some scans
and passed every test. The FMEA proposes the requirement; MiniDAQ adopted it as SRS-SRT-012
with the test `CoincidenceSorter.TiesKeepTheEarlierPair`.

**Occurrence.** Take the row "window boundary off by one picosecond". An occurrence rating
would be a guess at how likely a developer is to write `<` for `<=`: there is no population
of such defects to count, and once the code is written the defect is either there or not. If it
is there, it acts on every scan. What the row rates instead is the severity of the effect and
the detection: a unit test with a partner exactly one window later finds the defect every
time, so the control is a test, not a probability.

**Why the end of run is a sorter function.** The sorter closes windows only when a later single
proves them complete, so its last windows depend on `flush()`, which the pipeline calls. A
failure there loses data without a counter, which is the worst kind of failure in this FMEA:
the accounting identity is what detects it.
