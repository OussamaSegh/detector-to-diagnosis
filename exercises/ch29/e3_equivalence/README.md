# Exercise 29.3 (S): Is the second implementation the same?

**Goal.** Write the check that a second implementation of a projector (the C++ one, a GPU one)
does what the reference does, so that a test can say "the same" and mean it. The check in
`tools/test_recon_cpp.py` compares the C++ projector with the numpy one this way.

**Time.** 45 minutes.

**Starter.** `starter/equivalence.py` runs. `assert_same(reference, candidate, rtol)` projects a
centered disc with both and compares the results with `np.allclose`.

**Acceptance** (`tests/test_equivalence.py`, with the projectors of `tests/projectors.py`: the
parallel-beam pair of Exercise 28.1 and variants of it):
- It accepts the same projector, and the same algorithm in float32 with `rtol = 1e-5`.
- It refuses, naming `forward`, `back` or `geometry` in the message: angles half a view off, `s`
  reversed, a backprojector that takes the nearest bin, a scale error of 1e-4 with `rtol = 1e-5`,
  and 43 radial bins instead of 41.

**Then, by hand.**
1. Which mistakes did the starter accept, and why could its disc not see them?
2. The float32 projector differs from the reference by about 1e-7. How do you choose `rtol` for
   comparing the C++ projector with the numpy one, and why relative to the largest value?
3. Why check the candidate's dot-product test as well, when its forward and back each match the
   reference? Answer in `NOTES.md`.

**Hints.** Use random data: an image and a sinogram with no symmetry. Compare both directions.
Compare shapes before values.
