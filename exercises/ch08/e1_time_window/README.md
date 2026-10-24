# Exercise 8.1 (E): The coincidence time window for a 30 cm ring

**Goal.** Compute how wide the prompt coincidence window must be so that no true
coincidence is lost to its width, first for photons that can cross the whole ring, then
for photons that come from inside a smaller field of view, and finally with the
detector's timing resolution added.

**Time.** 30 minutes.

**Starter.** `starter/time_window.py`: three functions that raise `NotImplementedError`.

**Acceptance** (`tests/test_time_window.py`, run by CTest as
`ch08/e1_time_window/<variant>/unittest`):
- `max_time_difference_ps(300)` is 1000.7 ps, within 0.1 ps: the time light needs to cross
  300 mm.
- `max_time_difference_ps` for a 200 mm field of view is two thirds of that.
- `prompt_window_ps(diameter_mm, ctr_fwhm_ps, k)` is the full width of a symmetric window
  `|dt| <= max + k * sigma`, where `sigma = ctr_fwhm_ps / 2.3548` is the standard
  deviation of a pair's time difference; for 300 mm, 300 ps and k = 3 it is 2,766 ps
  within 1 ps.
- `true_fraction_kept(half_width_ps, offset_ps, ctr_fwhm_ps)` is the probability that a
  true coincidence whose real time difference is `offset_ps` falls inside `|dt| <= half_width`;
  0.5 when the offset sits on the edge, and above 0.998 three sigma inside.

Then answer in a comment at the end of your file: MiniDAQ uses 4 ns by default. What
could justify a wider window than the 2.8 ns computed here, and what does the extra
width cost?

**Hints.** How far does light travel in 1 ns? Where along a line of response is the
annihilation when the time difference is largest?
