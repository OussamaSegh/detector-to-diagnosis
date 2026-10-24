# Exercise 8.4: notes on the solution

**Why rejection sampling.** The Klein-Nishina distribution of cos(theta) has no inverse
cumulative distribution in closed form that is pleasant to evaluate, but it is cheap to
evaluate and bounded by 2. Rejection sampling needs nothing more. Kahn's method (1954)
and the methods in production codes such as Geant4 and EGSnrc are faster; for a teaching
simulator the simplest correct method wins.

**What the starter got wrong.**
- The sign: with `1 -` instead of `1 +`, the scattered photon gains energy, and at large
  angles the denominator goes to zero. The 90 and 180 degree checks catch it at once.
- Isotropic scattering is the shortcut that "looks right" in an image: photons still
  scatter, the spectrum still has a Compton shoulder. But at 511 keV scattering is
  strongly forward, so an isotropic model produces too much large-angle, low-energy
  scatter, which an energy window then removes too easily. A scatter fraction computed
  with it is too optimistic.

**Why chi-square, and why these numbers.** 400,000 samples in 40 bins gives about 10,000
per bin, so a wrong shape is far outside the statistical spread, while the correct
sampler passes with a fixed seed every time. The threshold 80 for 39 degrees of
freedom corresponds to a p-value of about 1e-4 (verify: with a chi-square table or
`scipy.stats.chi2.sf(80, 39)`).
