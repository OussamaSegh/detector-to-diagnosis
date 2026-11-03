# Exercise 31.1 (E): Coincidences per crystal pair, through a memory map

**Goal.** Count the prompt coincidences of each crystal pair of an MDQ-L1 file, reading the
records through `np.memmap` and a structured dtype, without decoding them one by one.

**Time.** 45 minutes.

**Starter.** `starter/pairs.py` runs and returns arrays of the right types. It reads the whole
file with `np.fromfile`, keys a pair by (crystal_a, crystal_b) and counts every record.

**Acceptance** (`tests/test_pairs.py`):
- A pair is one key whichever of its two crystals saw the earlier single:
  lower id × 18,432 + higher id.
- Delayed coincidences (bit 15 of crystal_a) and tags (crystal_a 0x7FFF) are not counted.
- Over 50,000 coincidences in blocks of 777 records, the keys and counts equal a direct count.

**Then, by hand.**
1. Time `np.memmap(path)` alone, then the first operation on its records. Where is the file read?
2. Why may the records of a block be viewed as `RECORD` in place? What would break the view?
3. How much memory would a dense matrix of pair counts take for 18,432 crystals? Answer in
   `NOTES.md`.

**Hints.** The block header gives the number of records at byte 8; the records start 32 bytes
after the header's start. `np.minimum` and `np.maximum` order a pair; `np.unique(...,
return_counts=True)` counts keys.
