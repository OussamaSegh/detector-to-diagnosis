# Exercise 8.4 (M, extra): Sampling Compton scattering

**Goal.** Write the two functions a photon transport code needs for Compton scattering:
the energy after a scatter, and a sampler for the scattering angle that follows the
Klein-Nishina distribution. Then show statistically that your sampler is right.

**Time.** 1.5 hours.

**Starter.** `starter/compton.cpp`: the energy formula has a sign error, and the sampler
draws the angle uniformly in solid angle (isotropic scattering), the most common shortcut.

**Acceptance** (`tests/test_compton.cpp`):
- `compton_energy_kev(511, cos)` gives 511 keV at 0 degrees, half the energy at 90 degrees
  and a third at 180 degrees (for E = m_e c^2 = 510.999 keV exactly).
- 400,000 samples of `sample_cos_theta` at 511 keV and at 140 keV, in 40 bins of cos(theta),
  pass a chi-square test against the Klein-Nishina distribution (chi-square below 80 for
  39 degrees of freedom).
- The fraction of 511 keV photons scattered forward (cos > 0) is within 0.005 of the
  Klein-Nishina value, which the test computes by numerical integration.

**Hints.** The Klein-Nishina cross section per solid angle is proportional to
P^2 (P + 1/P - sin^2 theta), with P = E'/E. What is its largest value? A uniform cos(theta)
is a uniform direction in solid angle; how do you turn uniform proposals into samples of
a distribution you can bound?
