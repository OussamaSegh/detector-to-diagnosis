# Exercise 39.1: notes

The starter fails four of the five tests: it moves the point by c tau instead of c tau / 2 and
towards the wrong crystal, and it rounds tau to the nearest bin, which centers the bins on
multiples of the width instead of putting their edges there. Equal times pass by accident.

Design choices:

- l = c (t_a - t_b) / 2 from the middle, towards b: the photon that arrived later travelled
  further, so the annihilation is nearer the crystal that saw its photon first. The factor 2 is
  the one mistake everybody makes once: each photon's path changes by l, so their difference by
  2 l.
- Clamping to the segment keeps a point inside the scanner when timing noise near a crystal
  gives a tau longer than the line. A reconstruction does not clamp: its kernel has tails beyond
  the line, and the projector simply has no image there.
- floor((2 tau + K w) / 2w) is the histogrammer's formula, in integers there. Python's `round`
  rounds half to even and towards the nearest, `int()` truncates towards zero; both put a
  negative tau in the wrong bin at some edge.
