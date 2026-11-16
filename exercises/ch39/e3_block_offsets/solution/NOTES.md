# Exercise 39.3: notes

The starter fails three of the four tests: without the geometry, an off-center source adds the
difference of the two path lengths to every time difference; its per-block mean charges each
block with its partners' offsets as well as its own; and it answers for a source at the center,
which cannot tell four pairs of blocks apart. The swap test passes: the starter is symmetric in a
and b, which is the one thing it gets right.

Design choices:

- Take out what the geometry predicts first. For a source at the center the two paths are equal
  and the prediction is 0; off center it is up to 2 x 60 mm / c = 400 ps, larger than the
  offsets being measured.
- One least-squares fit of all the offsets, not a mean per block: the leftover of an event is
  o_a - o_b, so a block's mean leftover is its own offset less the mean of its partners'. The
  normal equations have the Laplacian of the block pairs, as the time base monitor's do
  (Chapter 38, Exercise 38.3), here with one weight per event.
- The common constant cannot be measured from differences: fix the mean at zero over the blocks
  that saw events. A block with no event has no equation and is left out of the system, not set
  to zero, which would pull the mean.
- Events with both singles in one block carry no information about it and are skipped.
- Check that the events connect the blocks. A point source at the center is the obvious choice
  and the wrong one: every line through it joins a block to the one opposite, so the data hold
  four independent pairs, and a least-squares solver with a mean of zero would still return
  eight numbers. A source off center, or a cylinder, links neighbors too.
