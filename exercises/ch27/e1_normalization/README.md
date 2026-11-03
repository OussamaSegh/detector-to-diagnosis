# Exercise 27.1 (M): Crystal efficiencies from a normalization scan

**Goal.** Find each crystal's relative efficiency from the coincidences of a normalization scan,
for any source whose projection you know, and normalize another scan with it. This is the
crystal component of `tools/recon/corrections.py`, without its assumption that every crystal of
a ring sees the source alike.

**Time.** 90 minutes.

**Starter.** `starter/norm.py` runs. `efficiencies` divides each crystal's fan sum by the mean
fan sum, which is right for a source that every crystal sees alike and a scanner with many
partners per crystal. `normalize` divides each line by the mean efficiency of its two crystals.

**Acceptance** (`tests/test_norm.py`, a scanner of 4 rings of 96 crystals with efficiencies of
0.90 +- 0.05; `counts[i, j]` holds the coincidences between crystals i and j, and `expected[i, j]`
what a perfect scanner would record from the same source):
- A cylinder centered in the ring and 40,000 counts per crystal: the efficiencies within 1.3
  times the Poisson error rms, none beyond 6 times, mean 1.
- The same cylinder 40 mm off center: the same limits.
- A second scan, of a smaller source off center, normalized with the first scan's efficiencies:
  no pattern of the crystals left in its fan sums, and the scan's shape that of the perfect
  scanner.
- A dead crystal (efficiency 0): its efficiency comes out 0, `normalize` names it, and every one
  of its lines is 0, not infinite.

**Then, by hand.**
1. How many counts per crystal does a normalization scan need for 1% per crystal? With the
   simulator's normalization scan (`measurements/ch27`), how long is that at 10 MBq?
2. Why did the starter fail even for the centered cylinder on this small scanner, when
   `tools/recon` uses the same one-step ratio for MiniDAQ's 18,432 crystals?
3. The physicist recalibrates the energies (Chapter 26) and keeps the old normalization. What
   changes, crystal by crystal, and which requirement stops it? Answer in `NOTES.md`.

**Hints.** On average `counts[i, j] = eff[i] eff[j] expected[i, j]`, so a fan sum is
`F[i] = eff[i] * sum_j eff[j] expected[i, j]`. Solve it for `eff[i]` and iterate. Leave the
overall scale of the efficiencies at mean 1: a normalization only fixes them relative to each
other.
