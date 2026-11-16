# Exercise 39.1 (E): Where along the line

**Goal.** From the two time stamps of a coincidence, find where on its line of response the
annihilation happened, and the TOF bin MiniDAQ's histogrammer puts it in.

**Time.** 1 hour.

**What to write** (`where.py`):
- `position(a, b, t_a_ps, t_b_ps)`: `a` and `b` are the (x, y) positions in mm of the two crystals,
  `t_a_ps` and `t_b_ps` the times at which they saw their photons. Return the (x, y) of the
  annihilation, on the segment from `a` to `b`. Light travels 0.299792458 mm per picosecond.
- `tof_bin(tau_ps, bins, width_ps)`: the bin of tau = t_a - t_b among `bins` bins of `width_ps`,
  centered on 0 when `bins` is odd, as `minidaq::sino::Histogrammer` bins it: bin k holds tau in
  [(k - bins/2) w, (k + 1 - bins/2) w). Return None outside every bin.

**Starter.** `starter/where.py` moves the point from the middle towards the crystal that saw its
photon first, by c times tau, and rounds tau to the nearest bin.

**Acceptance** (`tests/test_where.py`):
- A point source anywhere inside the ring is found to 1e-6 mm from its two arrival times, whichever
  crystal is called a; equal times give the middle of the line.
- A time difference beyond the line's length is clamped to the nearer crystal.
- The bins of 5 x 100 ps and of 4 x 100 ps put each edge in the bin above it, and tau outside the
  bins gives None.

**Then, by hand.**
1. A scanner of 300 mm diameter and a coincidence time resolution of 250 ps FWHM: how many
   resolution elements fit along a line through the center?
2. Why does the histogrammer fix which crystal of a line is endpoint a, instead of using the
   earlier single?
3. The time stamps are quantized to 5 ps by the readout link. What does that do to the position?
