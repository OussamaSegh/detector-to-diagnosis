# Exercise 27.2 (M): The randoms of every line

**Goal.** Estimate the random coincidences of every line of response in two ways: from the
singles rates of its two crystals, and from the delayed coincidences with their noise removed.
These are the two estimators of `tools/recon/corrections.py`, on a ring small enough to check by
hand.

**Time.** 90 minutes.

**Starter.** `starter/randoms.py` runs. `from_singles` returns `tau s_i s_j` with `s` the counts
of the run. `variance_reduced` returns `D_i D_j / sum(D)`, with `D_i` each crystal's delayed fan
sum, the textbook formula for a scanner in which every crystal meets every other.

**Acceptance** (`tests/test_randoms.py`, one ring of 192 crystals, singles of 20 to 60 kHz higher
on one side, a coincidence window of 4 ns and 60 s; `fan[i, j]` is True where the sorter accepts
the pair, within +-48 crystals of opposite):
- `from_singles` gives `2 tau r_i r_j` counts in the run for the rates `r`, 0 outside the fan,
  symmetric.
- `variance_reduced` of Poisson delayed coincidences: 0 outside the fan; the total within 0.3% of
  the truth; each crystal's fan sum within 4.5 times the Poisson error of the delayed counts in
  its fan; the noise per line less than 0.15 times that of the delayeds.
- The same with a fan of +-16 crystals.

**Then, by hand.**
1. A line of this ring holds about 700 randoms in the run, and the variance reduction cuts their
   noise by a factor of 7. In the simulated phantom of `measurements/ch27`, how many randoms does
   a sinogram bin hold on average, and what would subtracting the raw delayeds do to it?
2. `tools/recon` estimates MiniDAQ's randoms from the singles in the run record. The first
   version took every single in the energy window and came out 31% high. Why, and what fixed it?
3. The delayed window of MiniDAQ's sorter estimates the randoms 7% high (`measurements/ch27`).
   Which rule of Chapter 10 makes that, and which estimate would you give the reconstruction?
   Answer in `NOTES.md`.

**Hints.** On average the delayeds factorize, `D[i, j] = x[i] x[j]` on the fan, so a crystal's fan
sum is `x[i] * sum over its fan of x[j]`. Solve that for `x` by a fixed point, as in Exercise
27.1, and damp each step with the geometric mean of the old and the new value.
