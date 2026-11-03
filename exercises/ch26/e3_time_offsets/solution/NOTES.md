# Exercise 26.3: notes on the solution

**The three mistakes.**

- *No check that the graph is connected.* The pairs measure only differences d_i - d_j, so
  each connected part of the graph has its own unknown constant. A point source at the centre
  joins each crystal with the one opposite it and nothing else: 768 parts of two crystals in the
  acceptance test. The starter answered 1 and solved anyway; the solution gives each crystal the
  smallest label among its partners' until nothing changes, and refuses more than one part.
- *A mean is one step of a solver, not the solution.* For crystal i, the mean of its pairs'
  differences seen from its side is d_i minus the mean delay of its partners. With partners
  spread over a fan of 120 crystals whose delays are 600 ps rms, that mean is about 55 ps rms:
  the starter's 53 ps error, with no noise at all. Conjugate gradients on L d = r solve all the
  equations together.
- *A fixed window is not a test of the residual.* The starter dropped pairs whose raw time
  difference was beyond 2 ns, but the delays themselves make true differences of up to 3 ns,
  and the randoms inside 2 ns stay. The residual after a solution is what a random has and a
  true pair does not: the solution drops pairs beyond four robust sigmas of the residual and
  solves again.

**Iterations** (Then, by hand, 2). With 120,000 pairs, the solver stopped (residual reduced by
1e-8) after 13 iterations for a fan of 60, 37 for a fan of 10 and 143 for a fan of 2, and the
delays' error went from 10 to 11 to 24 ps rms. Conjugate gradients converge in a number of
iterations that grows with the square root of the condition number of L. Its smallest nonzero
eigenvalue (the algebraic connectivity) is small when the graph is nearly in pieces: a narrow
fan makes a long chain around the ring, a point source makes pieces. The measurement's point
source took 740 iterations and its delays were 130 ps wrong (`measurements/ch26`).

**A source off centre** (3). A line of response whose midpoint is not where the activity is
centred gets a mean time-of-flight difference: the projection x of the source's offset on the
line gives 2x / c, 133 ps for 20 mm along the line. The pairs of a crystal see the offset from
their own direction, so the solution absorbs a pattern around the ring, a sinusoid with up to
about plus or minus 67 ps, into the delays. The procedure cannot see it: its residual is no
larger. Either the source is placed on the axis with a jig, or its position is measured from
the data (the time-of-flight image of the source) and its flight times subtracted before the
solution.
