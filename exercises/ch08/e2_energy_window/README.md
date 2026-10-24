# Exercise 8.2 (E): An energy window for 10% resolution

**Goal.** Given a detector with 10% energy resolution (FWHM) at 511 keV, choose an energy
window and justify both edges with numbers: how much of the photopeak each edge keeps,
and which scattered photons the lower edge rejects.

**Time.** 45 minutes.

**Starter.** `starter/energy_window.py`: four functions that raise `NotImplementedError`.

**Acceptance** (`tests/test_energy_window.py`):
- `sigma_kev(0.10)` is the standard deviation of the photopeak, 21.7 keV.
- `photopeak_fraction(lo, hi, resolution)` is the fraction of 511 keV photons measured inside
  `[lo, hi]`; for 10% and `[450, 613]` it is above 0.99.
- `scattered_energy_kev(theta_deg)` is the Compton formula; 255.5 keV at 90 degrees.
- `min_rejected_angle_deg(lo)`: the smallest single-scatter angle whose photon falls below
  `lo` if it were measured exactly; for 450 keV it is 30.2 degrees within 0.1.
- `choose_window(resolution)` returns `(lo, hi)` with a photopeak fraction of at least 0.95,
  a lower edge of at least 425 keV, and an upper edge of at most 650 keV; for 10% and for
  15% resolution.

Then write two sentences in a comment: why is the window asymmetric around 511 keV, and why
can a scattered photon still pass any lower edge you choose?

**Hints.** FWHM = 2.3548 sigma. Which events above 511 keV are there to reject at all?
