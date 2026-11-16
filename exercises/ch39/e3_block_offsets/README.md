# Exercise 39.3 (H): Block clock offsets from a point source

**Goal.** Measure each detector block's clock offset with a point source at a known place: the
time difference of every coincidence is what the geometry says plus the offsets of its two
blocks. This is how a timing calibration (Chapter 26) finds the offsets that the time base
monitor (Chapter 38) then watches, and what time of flight needs right.

**Time.** 3 hours.

**What to write** (`calibrate.py`): `block_offsets(events, source, blocks)`. Each event is
`(a, b, block_a, block_b, t_a_ps, t_b_ps)`: the crystals' (x, y) in mm, their blocks, and the time
stamps the blocks gave. A block whose clock runs `o` late stamps every single `o` late. Return a
list of `blocks` offsets in picoseconds with a mean of zero over the blocks that saw events, and
None for a block that saw none.
- The time difference that the geometry predicts for an annihilation at `source` is
  `(|source - a| - |source - b|) / c`; what is left over is `o_a - o_b` plus timing noise.
- Fit all offsets at once by least squares: a block's leftover depends on its partners' offsets.
- Raise ValueError when the events do not connect the blocks into one group: the offset of one
  group against another is then not measured.

**Starter.** `starter/calibrate.py` takes the mean time difference `t_a - t_b` per block, adds it
to a's offset and subtracts it from b's, and ignores the geometry.

**Acceptance** (`tests/test_calibrate.py`, 8 blocks of 45 degrees on a ring of 156 mm, 40,000
coincidences with a resolution of 300 ps FWHM):
- A source at the center joins each block only to the one opposite: ValueError.
- A source 60 mm off center and offsets of up to 300 ps: every offset within 8 ps.
- A block that saw nothing is None, and the others still have a mean of zero.
- Calling either crystal of an event a gives the same answer.

**Then, by hand.**
1. Why can a point source give absolute offsets (up to a common constant) while the time base
   monitor of Chapter 38 only measures changes from the start of a run?
2. How many coincidences does a block need for an offset to 5 ps, with a resolution of 300 ps?
3. A source position known only to 2 mm: what error does that leave in the offsets, and does it
   matter for time of flight?
