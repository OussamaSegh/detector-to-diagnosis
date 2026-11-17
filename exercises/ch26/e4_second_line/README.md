# Exercise 26.4 (M): A second energy line

**Goal.** Write the check that sees what the acceptance criteria of Chapter 26 cannot: a wrong
saturation energy E_sat. A wrong E_sat still puts every photopeak at exactly 511 keV, because
the gain is found from the photopeak with that E_sat; only a line at another energy shows the
curve is wrong. Then find E_sat itself from the two lines.

**Time.** 45 minutes.

**The second line.** LYSO crystals contain lutetium-176, which decays with gamma rays of 202 and
307 keV. A crystal opposite the decaying one, in coincidence with its beta, sees the 307 keV
gamma as a clean line: the intrinsic-radiation check that many LYSO scanners run without a source
(assumption: confirm with team how your scanner measures it). Here each crystal's 307 keV peak
code is given, with its 511 keV photopeak code.

**Starter.** `starter/second_line.py` runs, and its `check_e_sat` passes every calibration.
`saturate` and `energy_of` are correct. `check_e_sat` checks each crystal's photopeak, and
`estimate_e_sat` returns infinity.

**Acceptance** (`tests/test_second_line.py`, 40 crystals with a 10% gain spread, E_sat 1,500 keV):
- `energy_of` puts the photopeak at 511 keV and the line at 307 keV.
- The right E_sat passes, also with each peak's center 0.2% off at random.
- An E_sat of 1,200, 1,800 or 3,000 keV, or none (a linear detector), is refused: each puts the
  photopeaks at 511 keV and the line more than 0.8% off.
- `estimate_e_sat` finds 900, 1,500 and 2,500 keV from exact codes, and the median of 40 noisy
  crystals' estimates is within 10% of 1,500 keV.
- A linear detector gives infinity, also when noise puts the ratio of the codes above 511 / 307.

**Then, by hand.**
1. How far does the 307 keV line move for an E_sat 20% too high, and for one 20% too low? What
   does that say about the tolerance of 0.8% and the precision of a peak's center?
2. Why is the median of 40 crystals' estimates of E_sat close to the truth when each one is not?
   When would one of them come out infinite?
3. Which energies would make a better second line, and why is 662 keV (caesium-137) worse than
   307 keV here? Answer in `NOTES.md`.

**Hints.** The check is the starter's with the line's code and energy instead of the photopeak's.
The ratio S(511) / S(E) grows with E_sat towards 511 / E; solve for E_sat by bisection on its
logarithm.
