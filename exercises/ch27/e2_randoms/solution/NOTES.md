# Exercise 27.2: notes on the solution

**The three mistakes.**

- *A random pair needs the second single within tau either way round.* A single at time t pairs
  with any single of the other crystal between t - tau and t + tau: a window of 2 tau, so the rate
  is `2 tau r_i r_j` with `r` in singles per second, and the run holds that times its length. The
  starter used counts for rates and one tau, which is wrong by the factor `2 / seconds`: in a run
  of 60 s it was 120 times too small.
- *The Casey formula assumes every crystal meets every other.* `D_i D_j / sum(D)` is right when
  `sum(D)` is the sum over the partners that crystal i can meet. On this ring a crystal meets 97
  of 191 crystals, so the formula gave half the randoms (0.50 of the truth), and with the narrow
  fan of +-16, 33 crystals, a sixth (0.17). The fixed point uses each crystal's own fan, so its
  estimate keeps every crystal's fan sum and is right for any fan.
- *The noise is what the method is for.* A line here holds 711 randoms, Poisson noise of 27; the
  estimate's noise is 3.9, 0.15 times as much, because each line now rests on two fan sums of
  69,000 counts. What remains is the noise of those fan sums: no estimator from these delayeds
  does better per crystal, which is why the test counts in its standard deviations.

**Counts per bin** (Then, by hand, 1). The phantom run of `measurements/ch27` holds about 118,000
randoms in a sinogram of 95 slices, 192 views and 227 bins, about 4 million bins: 0.03 per bin.
The raw delayeds of a bin are almost all 0 and a few 1, so subtracting them puts noise of the
size of the signal into every bin and makes negative counts; the estimate from fan sums or from
singles has none of that.

**The singles bias** (2). Under the kill-all rule of Chapter 10 a single that is part of a prompt
coincidence is used and cannot also be part of a random pair. The first version counted it, and
the 31% excess was the share of the windowed singles that were already paired. Subtracting each
crystal's prompt count from its singles before the product left 1.8% (`measurements/ch27`).

**The delayed window** (3). The same kill-all rule removes some delayed pairs and the windows of
singles near each other in time, and the delayed stream does not lose randoms the way the prompt
stream does: the estimate is 7% high, the bias Chapter 10 measured. The estimate from singles,
with the paired singles taken out, is closer here and costs no second window; the delayeds remain
the check that it is in the right range. That is a choice of the team that validates the
corrections (assumption: confirm with team).
