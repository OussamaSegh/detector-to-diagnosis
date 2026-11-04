# Exercise 35.1 (E): A number a reader gets back

**Goal.** Write a PET slice's scale factor as a DICOM Decimal String and store the slice's values
as 16-bit integers, so that a viewer that reads the file gets every value back within half a
step. The rescale slope is text in the file, at most 16 characters; whatever the viewer reads is
that text, not the number in your program.

**Time.** 1 hour.

**What to write** (`ds.py`):
- `format_ds(x)`: the text of a DS for `x`, at most 16 characters, with as many significant digits
  as fit; `ValueError` for a value that is not finite.
- `quantize(plane)`: `(stored, slope_text)` for a 2-D numpy array of values that are not
  negative: `stored` is `uint16`, `slope_text` is `format_ds` of the slope, and the slope is the
  largest value over 65535 (1 for an empty plane). Compute the stored values with the slope as
  written (`float(slope_text)`).

**Starter.** `starter/ds.py` writes six decimals, as a quick `f"{x:.6f}"` does, and divides by the
slope it computed, not the one it wrote.

**Acceptance** (`tests/test_ds.py`):
- Every DS is at most 16 characters and within 5e-10 of the value, relatively, for values from
  1e-12 to 1e12, negative ones too; a slope of 1.4e-7 does not become 0; NaN and infinity raise.
- Every stored value times the written slope is within half of that slope of the value, for a
  plane whose slope is a long decimal; the largest value is stored as 65535; an empty plane has a
  slope of 1.

**Then, by hand.**
1. The image of Chapter 33's phantom has a largest value of about 0.0094 (proportional counts).
   What would a viewer show for it with the starter's slope?
2. Why compute with `float(slope_text)` and not the slope you divided by? How large can the
   difference be with 16 characters, and when would it matter?
3. Where else in a DICOM file is a number written as text? Name two attributes whose precision
   matters to a measurement on the image.
