# Exercise 28.3 (S): Ordered subsets

**Goal.** Speed up the MLEM of Exercise 28.2 by updating the image once per subset of the views,
as `tools/recon/mlem.py` does, and choose the subsets and the sensitivity so that four
iterations of five subsets reach what twenty iterations of MLEM reach.

**Time.** 45 minutes.

**Starter.** `starter/subsets.py` runs. `subsets` splits the views into consecutive blocks.
`osem` computes the sensitivity once, for all the views, and divides it by the number of
subsets. The projector in `tests/projector.py` takes a list of views.

**Acceptance** (`tests/test_subsets.py`, 32 x 32 unit pixels, 36 views, 41 radial bins, and
multiplicative factors that change from view to view, between 0.3 and 0.9):
- `subsets(36, 5)` holds every view once, in subsets whose sizes differ by at most one, and no
  subset leaves a gap of more than 6 views around the half turn.
- `subsets` refuses 0 subsets and more subsets than views with `ValueError`.
- Started at the true image with noiseless data, 3 iterations of 5 subsets stay at the truth to
  1e-9.
- A disc with a hot rod, noiseless and then with Poisson noise: 4 iterations of 5 subsets within
  3% rms (of the disc's mean) of 20 iterations of MLEM, and with the same total activity within
  1%.

**Then, by hand.**
1. 36 views do not divide into 5 subsets. How large is each subset's sensitivity compared with
   the full one divided by 5, and what does the starter's shortcut do to the image?
2. Keep the per-subset sensitivity and the consecutive blocks. How far from MLEM is it, and why
   does the order of the views matter?
3. MiniDAQ's reconstruction (Chapter 28) uses 8 subsets of 192 views. How many views per subset,
   how far apart, and why would 192 subsets be a bad idea? Answer in `NOTES.md`.

**Hints.** An OSEM update is an MLEM update in which the data are only the subset's views: its
backprojection and its sensitivity both run over those views alone. A subset is a good stand-in
for all the data when its views spread over the whole half turn.
