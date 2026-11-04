# Exercise 35.2 (M): Where is this pixel in the patient?

**Goal.** Give an exported slice the three attributes that place it in the patient: Image Position
(Patient), Image Orientation (Patient) and Pixel Spacing. A viewer uses them to show the slice the
right way up, to put the patient's left on the correct side, to measure distances and to fuse
the PET with a CT. None of the mistakes this exercise is about makes an image look wrong.

**Time.** 2 hours.

**The frames.** The reconstruction's image is an array `[row, column]` in the gantry frame: x along
a row, to the right seen from the front of the gantry; y up, the row index growing with y; pixel
centers symmetric about the axis; the slice at gantry `z_mm`. DICOM's patient frame (LPS): x to
the patient's left, y to the patient's back (posterior), z to the head. For a patient on their
back, head first (HFS), gantry (x, y, z) is LPS (x, -y, z); feet first (FFS), (-x, -y, -z).

**What to write** (`plane.py`):
- `export_rows(image)`: the array as it is written to the file, first row the highest gantry y
  (so that the image's columns point to the patient's back, as viewers expect).
- `plane(shape, row_mm, col_mm, z_mm, position)`: a dict with `ImagePositionPatient` (the LPS
  position of the center of the first exported pixel), `ImageOrientationPatient` (six direction
  cosines: along a row, then down a column) and `PixelSpacing` (`[spacing between rows, spacing
  between columns]`, in that order). `row_mm` is the distance between rows (along gantry y),
  `col_mm` between columns. `ValueError` for a position other than HFS and FFS.
- `to_patient(ipp, iop, spacing, r, c)`: the LPS position of the center of exported pixel `(r, c)`.

**Starter.** `starter/plane.py` writes the rows as they come, writes Pixel Spacing as
`[column, row]` and reads it the same way, and treats every position as HFS.

**Acceptance** (`tests/test_plane.py`):
- A pixel off the axis, at gantry x = +19 mm, y = +29 mm, lands at LPS (19, -29, z) for HFS and at
  (-19, -29, -z) for FFS, with square and with non-square pixels.
- Pixel Spacing is row spacing first; the orientation's two directions are unit vectors and
  perpendicular; for HFS the column direction is +y (posterior).
- An unknown position raises.

**Then, by hand.**
1. Which of the starter's three mistakes would a radiologist notice on a single slice? Which only
   when the PET is fused with a CT? Which never, until someone measures a lesion?
2. Why do square pixels hide the order of Pixel Spacing? What test data would you keep for a
   product so that it cannot hide again?
3. Prone positions (HFP, FFP) are refused. What would you need from your team before adding them?
