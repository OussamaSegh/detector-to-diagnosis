# Exercise 26.2 (M): A flood map and its crystal lookup table

**Goal.** From a flood of one detector block (events with positions u and v, both 0 to 1,
from the light sharing between photodetectors), find the 256 crystals of a 16 by 16 block,
put them in the order of the crystals, and build the lookup table that names the crystal of
every pixel. MiniDAQ's boards do this themselves; this is what their calibration does.

**Time.** 90 minutes.

**Starter.** `starter/flood.py`: `flood`, `smooth`, `lut` and `identify` are given and
correct. `find_peaks` returns the 256 highest pixels of the flood; `arrange` puts each peak
in the grid cell that a regular 16 by 16 grid would give it.

**Acceptance** (`tests/test_flood.py`, a synthetic block whose edges are compressed and
whose rows bend, 400 events per crystal and a blur of 1 pixel):
- 256 peaks, one per crystal, each within 1.5 pixels of the crystal's true centre.
- `arrange` gives every crystal its own cell, within 1.5 pixels of its centre.
- The lookup table names the right crystal for more than 98% of the events.
- A more compressed block with 150 events per crystal: median position error under 0.7
  pixels, worst under 2, and more than 95% of the events identified.
- `arrange` refuses a number of peaks other than 256.

**Then, by hand.**
1. Draw the flood and the table's boundaries (matplotlib). Which crystals are hardest to
   tell apart, and why are they the ones at the edges?
2. The table assigns each pixel to the nearest peak. Where does that put the boundary
   between two peaks of different brightness, and where would the valley between them put
   it? Which events does each choice misassign?
3. A board is recalibrated after its photodetectors are replaced. Which of the steps of this
   exercise can be checked automatically, and what should a person still look at? Answer in
   `NOTES.md`.

**Hints.** One peak per blob: a pixel is a peak if no pixel within two pixels of it is
higher, in the smoothed flood. Then order: the 16 highest peaks in the image are the first
row, whatever their spacing. Pixel k covers positions k to k + 1.
