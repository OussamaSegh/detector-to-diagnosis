# Exercise 10.1: notes on the solution

**Energy first.** The energy window is applied before windowing. If you windowed first
and dropped low-energy singles afterwards, a scattered 300 keV photon would still turn a
clean pair into a multiple, and the pair would be lost. Real sorters differ on this point;
what matters is that the order is stated and tested (MiniDAQ's `CoincidenceSorter` and the
Chapter 8 counter both apply it first).

**Indices, not copies.** Returning indices keeps the link to the truth. A sorter that
returns copies of the singles has to look them up again, by (time, crystal) as
`minidaq_sim` does; that works because the simulator never produces two singles with the
same time and crystal, an assumption that the lookup counts and reports.

**Exact, not approximate.** The test compares counts exactly. When the reference and the
fast sorter disagree, the difference is a list of pairs you can print, which points
straight at the rule that differs.
