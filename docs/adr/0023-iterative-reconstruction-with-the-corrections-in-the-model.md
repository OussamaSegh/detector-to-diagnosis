# 0023. Iterative reconstruction with the corrections in the model

Date: 2026-11-03
Status: Accepted

## Context

Chapter 27 gives, for every bin of a sinogram, what multiplies the activity along its line
(normalization, attenuation, live fraction) and what adds to it (randoms, scatter). The image
comes from these and the counts by a reconstruction, which the team builds as a tool next to the
corrections (`tools/recon`) and, in Chapter 29, moves its hot loop into C++. Four questions:

- the algorithm: analytic (filtered backprojection) or iterative (MLEM and its ordered subsets);
- where the corrections go: applied to the data before the reconstruction, or into its model of
  the data;
- the system matrix: stored, or computed from the geometry, and with which projector;
- the geometry: where the lines of response are.

## Options

The algorithm:

1. **Filtered backprojection.** Linear, fast, with a known noise and resolution. It needs
   corrected data and treats every bin as equally certain, so its images of low-count data have
   streaks.
2. **MLEM and OSEM.** MLEM maximizes the Poisson likelihood of the counts, keeps the image
   non-negative and weights each bin by its own counts; it is slow, and its noise grows with the
   iterations. OSEM (Hudson and Larkin, 1994; verify: IEEE Trans. Med. Imaging 13(4), 601-609)
   updates once per subset of the views and reaches in one iteration of k subsets about what
   MLEM reaches in k.

The corrections: applied to the data, `(y - b) / m`, which is then no longer Poisson, has
negative bins and has no value where `m = 0`; or in the model, `ybar = m A x + b`, with the
counts as measured.

The matrix: for the 2D sinogram of 192 views and 227 bins and an image of 128 x 128 pixels, a
ray-driven projector has about 11 million weights, 89 MB stored with their indices; in 3D, with
the oblique planes, it is orders of magnitude larger. The projector: Siddon's exact intersection
lengths, Joseph's interpolation one column or row at a time, or a pixel-driven splat.

## Decision

- OSEM with interleaved subsets, every k-th view in each, and each subset's own sensitivity
  (SRS-REC-003). MLEM is OSEM with one subset. Filtered backprojection stays a reference to
  compare against, not the product's reconstruction.
- The corrections in the model: `ybar = m A x + b`, the counts never changed, a bin with
  `m = 0` without weight in the update and in the sensitivity (SRS-REC-002).
- Joseph's projector, matrix-free: its weights computed from the geometry and kept per view in
  the numpy tool (89 MB, built in 0.3 s), the backprojection with the same weights so that it is
  the exact adjoint (SRS-REC-001). Chapter 29 computes them on the fly in C++.
- Each bin's own line: the two normal angles that a view interleaves and `s = -R sin(pi r / N)`.
  The radius of the lines is a parameter of the reconstruction, not the crystals' front face:
  a point source comes out 3.6% too close to the axis with the lines at 150 mm and within 0.3%
  at 156 mm (measurements/ch28), because the photons interact on average below the front face.
- 2D, of the slices summed, for an object that is uniform along the axis. 3D and the oblique
  planes are the next step (assumption: confirm with team whether your reconstruction is fully
  3D or rebins to 2D).
- A tool of class T3 (TL-31) in the same package as the corrections, because it shares their
  readers and their geometry, with its own tests and its own entry in the tool list.

## Consequences

### Positive

- The statistics the algorithm assumes are those of the data: the likelihood never decreases
  for MLEM, low-count bins are neither clipped nor amplified, and the gaps between blocks need
  no interpolation (Exercise 28.2 measures what pre-correction costs: a background 2.3 times as
  biased and stripes along the gaps).
- A change of a correction is a change of the model's `m` or `b`, not of the algorithm.
- The adjoint and the geometry each have a test that fails when they are wrong (H-13, RC-41 and
  RC-42).

### Negative

- The image depends on the number of iterations and subsets, and its noise grows with them: on
  the phantom of measurements/ch28 the background noise is 19.5% after 4 iterations of 8 subsets
  and 80.6% after 32, while the contrast of the largest rod is reached by iteration 3. The number
  of iterations, the subsets and the post-filter are protocol settings that the image-quality
  measurements of Chapter 30 must set and validate.
- The effective radius of the lines is a measured number, 156 mm on the simulator; a scanner's
  must be measured with a point source and kept with its calibration.
- The numpy tool takes 54 ms for a forward and 44 ms for a back projection of one 2D sinogram on
  the reference machine: fine for 2D, too slow for 3D. Chapter 29 moves the projector to C++.
- A single realization's contrast recovery varies by about 0.1 between noise realizations and
  is biased by about +0.08 by the scatter estimate of Chapter 27; the model check uses noiseless
  data and several realizations, not one image.
