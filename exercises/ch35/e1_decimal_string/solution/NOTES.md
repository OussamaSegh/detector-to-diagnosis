# Exercise 35.1: notes

The starter fails four of the five tests: six decimals turn any slope below 5e-7 into
`0.000000`, so the image of Chapter 33's phantom (largest value 0.0094, slope 1.4e-7) would read
as zero everywhere, and large values do not fit in 16 characters at all.

Design choices:

- `%.Ng` with N from 16 down: the first that fits keeps the most digits. A value with an exponent
  keeps at least 10 significant digits (`-1.234567890e-09` is 16 characters), which bounds the
  relative error at 5e-10.
- The stored values are computed with `float(text)`. With 16 characters the two slopes differ by
  less than 1e-15 relatively for a plain decimal and 5e-10 with an exponent: half a step is never
  exceeded at the brightest pixel only because the written slope is the one used. The rule costs
  nothing and makes the bound a property of the code, not of the numbers.
- `np.clip` before the cast: rounding can reach 65535.5 only if the written slope were smaller than
  the true one by more than the rounding allows, but a cast of an out-of-range float to `uint16`
  wraps silently, and silently is the word to avoid.
- To the questions: the starter's file shows 0 for every pixel. Pixel Spacing, Slice Thickness,
  Image Position (Patient), Radionuclide Total Dose and Radionuclide Half Life are DS too; a dose
  or a half-life cut to six decimals changes a standardized uptake value.
