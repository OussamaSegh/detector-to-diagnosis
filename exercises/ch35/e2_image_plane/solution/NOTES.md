# Exercise 35.2: notes

The starter fails five of the six tests. Each of its mistakes gives an image that looks right:

- Rows not flipped, with an orientation that says the column direction is posterior: the image is
  upside down in the patient frame. On one slice a reader sees the patient's back at the top and
  may notice; in a fused PET/CT the activity sits mirrored about the axis, which is worse.
- Pixel Spacing as [column, row], read back the same way: the writer's own reader agrees with
  itself, and square pixels hide it entirely. Only non-square pixels (or another reader) show it,
  and the symptom is a lesion measured with the wrong size in one direction.
- FFS treated as HFS: left and right exchanged for every feet-first patient, and the slices in the
  wrong order along z. Nobody sees it on one image.

Design choices:

- The geometry is one table of signs and two formulas; the exported array, the position of its
  first pixel and the orientation are computed from the same signs, so they cannot disagree.
- `+ 0.0` turns -0.0 into 0.0: a DS of "-0" is legal, but a diff between two files should not
  show a sign that means nothing.
- A product keeps test data with non-square pixels, an off-axis point and every supported
  position, and reads the files with a second implementation; square pixels and centered objects
  are the two habits that hide geometry defects.
- Prone positions need the gantry's frame and the patient support's direction from the hardware
  team, and a phantom with a marker on one side measured at the scanner: a table of signs is not
  evidence.
