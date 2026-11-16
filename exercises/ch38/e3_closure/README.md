# Exercise 38.3 (H): Block offsets with closure

**Goal.** Compute one clock offset per detector block from the measured shifts of pairs of
blocks, with its uncertainty, by weighted least squares, and say whether block clocks explain the
shifts at all. This is MiniDAQ's `solve_block_offsets` (Chapter 38) in Python.

**Time.** 3 hours.

**What to write** (`offsets.py`): `solve(n, pairs)` with pairs `(a, b, shift, variance)`, where
`shift` measures `o_b - o_a`. Return the offsets, their standard deviations, which blocks are
observed (in a connected group of two or more), the number of such groups, chi2 and the degrees
of freedom.
- Minimize the sum of `(shift - (o_b - o_a))^2 / variance` over the pairs.
- A constant added to every offset of a connected group changes no pair: fix each group's mean at
  zero, and report a block in no pair as unobserved with offset and sigma 0.
- chi2 is the minimized sum; the degrees of freedom are the pairs used less the observed blocks
  plus the groups.

**Starter.** `starter/offsets.py` walks a spanning tree from the first block of each group, puts
that block at zero and adds each pair's shift along the tree. It uses a handful of the pairs,
ignores the variances and computes neither uncertainties nor chi2.

**Acceptance** (`tests/test_offsets.py`):
- Exact shifts give the offsets with a mean of zero and chi2 0; two blocks and one pair of
  variance 400 give offsets of half the shift and sigma 10.
- Eight blocks, every pair measured with noise 20, one pair 100 times worse and declared so: the
  offsets are within 10 rms of the truth over 20 trials.
- Two groups are solved apart, each with a mean of zero; a block in no pair is unobserved.
- A pair with 300 added (a swapped cable) gives chi2 per degree of freedom above 50.

**Then, by hand.**
1. Why is the sum of the shifts around any loop of pairs zero for block clocks, and what does a
   nonzero sum tell you?
2. Why does a block's sigma fall as it has more partners, and what is it for a block in a chain
   of two?
3. Radio interferometry uses the same idea under the name closure phase. What plays the role of
   the block clocks there?
