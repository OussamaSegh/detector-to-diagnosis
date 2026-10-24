# Exercise 9.4 (E, extra): Time walk and time over threshold

**Goal.** Model a scintillator pulse as a difference of exponentials (0.5 ns rise,
40 ns decay, amplitude proportional to energy). Show that a fixed-threshold trigger fires
later for small pulses (time walk), and that a constant-fraction trigger does not. Then
show that time over threshold (ToT) grows with the logarithm of the energy, which is why a
ToT energy measurement needs a nonlinear calibration.

**Time.** 45 minutes.

**Starter.** `starter/time_walk.py` has the pulse model and a leading-edge trigger that
scans in 50 ps steps. Constant fraction and ToT are left as TODOs.

**Acceptance** (`tests/test_time_walk.py`, run with `ctest -R ch09/e4`):
- The leading-edge crossing is exact to 1 µV on the model pulse.
- The walk at 100, 200, 350, 511 and 650 keV decreases with energy and exceeds 20 ps at
  100 keV.
- Constant fraction at 10% has less than 0.01 ps of walk over the same energies.
- A pulse below the threshold never fires and has a ToT of 0.
- Doubling the energy from 300 to 600 keV adds τ_decay · ln 2 (27.7 ns) to the ToT, within
  2%.

**Hints.** Bisection converges to 1e-6 ns in about 30 steps. For constant fraction, which
threshold would make every pulse cross at the same time?
