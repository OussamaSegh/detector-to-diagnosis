# Exercise 11.1: notes on the solution

**Order of the stages.** Dead time acts in the detector, before anything is sorted, so
`measure` runs the simulator, then `sim::DeadTime`, then the sorter, and classifies each
prompt by looking its two singles up in the truth that left the front end (pile-up changes
an event's energy, not its time or crystal, so the lookup still works). The starter sorted
the simulator's output directly: its "dead time" changed nothing, which the test at
100 MBq catches.

**Scatters.** A pair from one decay is a scatter if either photon scattered in the
phantom: the line joining the two crystals no longer passes through the decay. The starter
counted those as trues; its scatter fraction is zero, against about a third for the
NEMA-style phantom in MiniDAQ's ring.

**The peak.** A count-rate sweep is measured on a geometric grid (5, 10, 20, 50, 100 ...),
which is even in x = ln A, and the curve's rise and fall are closer to symmetric there. The
vertex of the parabola through the best sample and its neighbors moves the estimate off the
grid; with a coarse grid the best sample alone can be off by half a step. On the test's
five-point sweep (half a million decays each) the solution finds the dead-time peak at
about 83 MBq.

**Answer to "Then, by hand"** (`measurements/ch11/countrate.txt`, 10 to 15 M decays per point,
peaks interpolated as above):

| Front end | NECR k = 1 peak | at | NECR k = 2 peak | at |
|---|---:|---:|---:|---:|
| no dead time | 73,500/s | about 560 MBq | 43,600/s | about 430 MBq |
| 1 µs non-paralyzable per block, pile-up | 16,100/s | about 73 MBq | 12,700/s | about 63 MBq |
| 1 µs paralyzable per block, pile-up | 15,500/s | about 67 MBq | 12,300/s | about 58 MBq |

Why does the curve without dead time peak at all? If the trues grew exactly as aA, the
scatters as bA and the randoms as cA², NECR = a²A / (a + b + kcA) would rise towards a limit
a²/(kc), about 124,000/s for k = 1 with this phantom's a and c, and never fall: randoms
alone flatten the curve, they do not bend it down. It falls because the trues grow more
slowly than A. Here the sorter's kill-all multiples policy discards more windows as the
rate rises (a third fewer trues per decay at 1000 MBq than at 100), and where the randoms
dominate, NECR ≈ T²/(kR) falls with them. k = 2 (a delayed-window subtraction) doubles the
randoms' weight, so the curve flattens earlier and its peak is lower and at a lower
activity.

With a 1 µs block dead time the peak moves down by almost an order of magnitude and drops
to about a fifth. At 70 MBq a block loses about 16% of its singles, a coincidence needs two
blocks to be live, and pile-up pushes recorded events out of the energy window. The
paralyzable front end peaks a little lower and earlier: every lost event extends its dead
time. Both models agree with each other below about 20 MBq, where nτ per block is small.

**Limits.** This is a NEMA-style test, not NEMA NU 2: the rates come from the ground truth,
not from the sinogram analysis the standard prescribes, the phantom is water rather than
polyethylene, and the dead time is an assumption for illustration (confirm with team for
the NeuroLF front end).
