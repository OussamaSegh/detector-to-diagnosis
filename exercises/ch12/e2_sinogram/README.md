# Exercise 12.2 (M): From list mode to a sinogram, in Python

**Goal.** Histogram a list-mode file into a 2D sinogram (192 views by 227 radial bins),
look at it, and get the point source back from its sinusoid. This is the plan's
"histogram list-mode into a 2D sinogram and view it in Python". Pure Python, no numpy:
the arithmetic of binning is the point.

**Time.** 2 hours.

**Starter.** `starter/sino2d.py` reads the file (`read_coincidences`, given and correct)
and has a binning that looks plausible and is wrong in three places: the view of a line
of response past 180 degrees, which coincidences are counted, and the position of a
radial bin. `fit_point` is complete; it fails only because of what it is given.

**Acceptance** (`tests/test_sino2d.py`, data in `tests/`):
- `lor_bin` gives the 73,536 lines of response of a ring 73,536 different bins, and the
  radial position of each bin is the line's distance from the axis, computed from the
  crystal positions.
- The sinogram of `point_source.mdql` (0.1 s of a 1 MBq point source at (40, -25) mm in
  air, written by `minidaq_sim --listmode`) has the 6,155 prompts, not the 12 delayeds,
  and is bin for bin what `minidaq_listmode sino` made of the same file.
- `fit_point` puts the source within 2.5 mm of (40, -25), and inside it.

**Then, by hand.**
1. Draw the sinogram: `python3 solution/sino2d.py tests/point_source.mdql sino.png`
   (needs matplotlib). Where is the sinusoid's amplitude, and its phase?
2. The fitted point is about 3.6% closer to the axis than the source. Run
   `minidaq_sim --source point --centre X,0,0 --phantom 0 --fov 120 --listmode DIR` for
   X = 0, 20, 47, 80, 100 and fit each. Is the error a shift or a scale? What in the
   detector model explains it, and what radius would remove it? Answer in `NOTES.md`.

**Hints.** The normal of the line between crystals i < j is at (i + j + 1) pi / 384;
what is it for i + j + 1 >= 384, and what happens to the sign of the distance? A
delayed coincidence is flagged in bit 15 of the first crystal. The positions of the
bins are not evenly spaced: the ring is a circle.
