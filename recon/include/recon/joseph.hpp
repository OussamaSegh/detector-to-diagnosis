// SPDX-License-Identifier: MIT
// The reconstruction's projector in C++ (Chapter 29): Joseph's method, matrix-free, with its
// exact adjoint. The same algorithm as tools/recon/project.py, which stays the reference.
//
// A sinogram bin is the line of points p with p . (cos phi, sin phi) = s. The image is n x n
// square pixels of pixel_mm, centered on the axis, stored row by row ([row, column] = [y, x]).
// A line closer to the y axis than to the x axis (decided per view, as the Python does) is
// stepped one column at a time, the others one row at a time; at each step the image is
// interpolated linearly between the two nearest pixels and weighted by the step's length.
// The weights are computed on the fly, so the projector holds only the lines, and back() uses
// exactly the weights forward() uses: it is the adjoint (SRS-REC-001).
//
// With time of flight (Chapter 39), each line is also split into TOF bins along its length: a
// step at position t along the line (from the foot of its normal, in the direction
// (-sin phi, cos phi)) contributes to bin k with the probability that a Gaussian timing error of
// the stated FWHM puts its time difference in that bin. The same as tools/recon/project.py's
// TofProjector (SRS-REC-007).
#pragma once

#include <cstddef>
#include <span>
#include <stdexcept>
#include <vector>

namespace recon {

// [snippet:tof]
// The time of flight of a projector: `bins` bins of `bin_ps` each, centered on a time difference
// of 0 when `bins` is odd, as MiniDAQ's histogrammer bins tau = t_a - t_b; a timing resolution of
// `ctr_fwhm_ps` (the coincidence time resolution, FWHM). bins == 1 is a projector without TOF.
struct Tof {
  std::size_t bins = 1;
  double bin_ps = 0.0;
  double ctr_fwhm_ps = 0.0;
};
// [/snippet:tof]

// [snippet:api]
class JosephProjector {
 public:
  // s_mm and phi: views x bins values each, view by view. Throws std::invalid_argument for sizes
  // that do not match, n == 0, a pixel size that is not positive, or a value that is not finite.
  JosephProjector(std::span<const double> s_mm, std::span<const double> phi, std::size_t views,
                  std::size_t bins, std::size_t n, double pixel_mm);
  // With time of flight; also throws for tof.bins == 0, or a bin width or a resolution that is
  // not positive when tof.bins > 1.
  JosephProjector(std::span<const double> s_mm, std::span<const double> phi, std::size_t views,
                  std::size_t bins, std::size_t n, double pixel_mm, const Tof& tof);

  std::size_t views() const noexcept { return views_; }
  std::size_t bins() const noexcept { return bins_; }
  std::size_t n() const noexcept { return n_; }
  double pixel_mm() const noexcept { return pixel_mm_; }
  std::size_t tof_bins() const noexcept { return tof_.bins; }

  // out[k * bins + b] = the line integral through image of bin b of view selected[k]. image has
  // n * n values, out selected.size() * bins. With TOF, out[(k * bins + b) * tof_bins + j] is the
  // part of it in TOF bin j, and out holds selected.size() * bins * tof_bins values.
  // threads = 0 uses the hardware's concurrency. The
  // result does not depend on the number of threads: each line is computed by one thread.
  void forward(std::span<const double> image, std::span<const std::size_t> selected,
               std::span<double> out, unsigned threads = 0) const;

  // The adjoint: image = A_S^T sino for the views selected (sino as forward's out). Each thread
  // accumulates its share of the views into an image of its own, and the images are added in
  // thread order, so the result is the same for every run with the same number of threads and
  // differs between thread counts only by rounding.
  void back(std::span<const double> sino, std::span<const std::size_t> selected,
            std::span<double> image, unsigned threads = 0) const;
  // [/snippet:api]

 private:
  struct View {
    bool along_x;  // step one column at a time
  };
  template <typename Visit>
  void walk(std::size_t view, std::size_t bin, const Visit& visit) const;
  // probability[j] for each TOF bin j of a step at position t along its line; the bins it
  // cannot reach (beyond 6 standard deviations) are 0, and first..last are the others.
  void tof_kernel(double t, std::span<double> probability, std::size_t& first,
                  std::size_t& last) const;
  void check(std::span<const std::size_t> selected) const;

  std::vector<double> s_, phi_;
  std::vector<View> view_;
  std::size_t views_, bins_, n_;
  double pixel_mm_;
  Tof tof_;
  std::vector<double> tof_edges_mm_;  // tof_.bins + 1 edges along the line
  double tof_sigma_mm_ = 0.0;
};

}  // namespace recon
