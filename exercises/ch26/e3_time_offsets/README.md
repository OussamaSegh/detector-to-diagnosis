# Exercise 26.3 (H): Channel delays by least squares

**Goal.** From the time differences of coincident pairs, find every channel's delay as the
least-squares solution of dt = d_i - d_j, by conjugate gradients without building a matrix,
refuse a set of pairs that does not connect every crystal, and set random coincidences
aside. This is `tools/calib/timing.py` on a scanner of four rings.

**Time.** 2 hours.

**Starter.** `starter/offsets.py` runs. `components` always answers 1. `solve` gives each
crystal the mean time difference of its pairs, seen from its side. `trimmed` drops the
pairs whose time difference is beyond 2 ns.

**Acceptance** (`tests/test_offsets.py`, 1,536 crystals with delays of 600 ps rms and a
coincidence time resolution of 127 ps rms):
- `components` counts the parts of small graphs and of a chain of 1,000 crystals, and finds
  more than 100 parts in the pairs of a point source at the centre, which `solve` refuses.
- With about 160 pairs per crystal from a centred cylinder, the delays come out within 15 ps
  rms; with exact differences, within 0.01 ps.
- With 15% random coincidences, `trimmed` still gets within 15 ps rms, sets more than 80% of
  the randoms aside and keeps more than 99% of the true pairs.

**Then, by hand.**
1. Why is the starter's mean wrong even without noise? Write what it computes for crystal i
   in terms of the delays of its partners.
2. How many iterations does conjugate gradients take here, and how does that change with a
   fan of 10 crystals instead of 60? What property of the graph decides it?
3. A cylinder placed 20 mm off centre: which pairs get a mean time-of-flight difference that
   is not zero, and how large is it? What does it do to the delays? Answer in `NOTES.md`.

**Hints.** L x is the degree times x minus the sum of the neighbours' x: two `bincount`s.
The right-hand side is the sum of dt over the pairs where the crystal is first minus the
sum where it is second. The constant is not measured: remove the mean at the end. For the
parts, give every crystal the smallest label among its partners' until nothing changes.
