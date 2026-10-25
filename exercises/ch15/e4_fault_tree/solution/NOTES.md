# Exercise 15.4: notes

**What the drawing hides.** The tree assumes that losing data (G1) and not noticing it (G2) are
independent. For E5, open windows not closed at the end of a run, they are not: that loss
happens on a path with no counter, so E5 causes E6 by itself. Drawn honestly, E5 is a single
point of failure, the one basic event that leads to the top event alone.

**The controls.** For the other losses, MiniDAQ's controls act on G2: the counters (RC-03) and
the integrity verdict (RC-01) make sure a loss is noticed, so two things must go wrong. For E5
detection cannot work, because nothing counts what is never processed, so the control has to
prevent the event: SRS-PIPE-012 requires that a stop processes all data already read, and its
test runs on every change. The accounting identity of the sorter (SRS-SRT-009) is a second
line: a single held in an open window at the end of a run is in no category, so the identity
fails in the sorter's tests.

A minimal cut set of order 1 is the first thing to look for in a fault tree, and a common cause
that the drawing does not show is the usual way one appears.
