# Exercise 30.4 (E): The uniformity of a uniform cylinder

**Goal.** Measure the integral and differential uniformity of an image of a uniform cylinder,
the daily check that the scanner's response is flat across the field, so that a gradient or a
defect shows and the noise and the blurred edge do not.

**Time.** 45 minutes.

**The definitions** (NEMA's uniformity of gamma cameras, used here on a transverse slice):
- integral uniformity: 100 (max - min) / (max + min) over the central field, the pixels within
  75% of the cylinder's radius;
- differential uniformity: the largest 100 (max - min) / (max + min) of any five consecutive
  pixels of a row or of a column inside the central field;
- both on the image smoothed once with the kernel [1 2 1; 2 4 2; 1 2 1] / 16, and only over
  pixels whose whole 3 x 3 neighborhood is inside the field.

**Starter.** `starter/uniformity.py` runs. `central_region` is correct. `smooth` returns the
image as it is; `uniformity` takes every pixel above zero and looks along the rows only.

**Acceptance** (`tests/test_uniformity.py`, a cylinder of radius 50 pixels whose edge is blurred
over 4):
- `smooth` keeps a flat level and spreads a single pixel into the kernel.
- A uniform cylinder: both numbers below 0.01%.
- A gradient of 5% from the center to the edge: integral 3.4 to 3.8%, differential below 0.3%.
- 2% noise per pixel: integral below 4% and differential below 3%.
- One whole row 10% low: differential above 2%, which only the columns show.
- A central field of fewer than 25 usable pixels raises `ValueError`.

**Then, by hand.**
1. What did the starter report for the uniform cylinder, and where did it come from?
2. With 2% noise per pixel, what are the integral uniformity without smoothing and with it, and
   the smoothed image's noise? Why is the kernel's effect on the noise a factor of about 0.38?
3. Which number would see a defective block of the scanner, and which a wrong normalization?
   Answer in `NOTES.md`.

**Hints.** Smooth with nine shifted copies of the image weighted by the kernel. A pixel is usable
when all nine of its neighbors are in the field. Run the five-pixel window along `s` and along
`s.T`, with the mask transposed too.
