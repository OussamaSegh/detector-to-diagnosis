// SPDX-License-Identifier: MIT
#include "recon/joseph.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <functional>
#include <limits>
#include <numbers>
#include <span>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace recon {
namespace {

unsigned thread_count(unsigned requested, std::size_t work) {
  const unsigned t = requested != 0 ? requested : std::max(1U, std::thread::hardware_concurrency());
  return static_cast<unsigned>(std::min<std::size_t>(t, std::max<std::size_t>(work, 1)));
}

// Runs body(first, last, thread) over [0, count) in contiguous chunks, one per thread.
template <typename Body>
void parallel_chunks(std::size_t count, unsigned threads, const Body& body) {
  if (threads <= 1) {
    body(std::size_t{0}, count, 0U);
    return;
  }
  std::vector<std::jthread> pool;
  pool.reserve(threads);
  for (unsigned t = 0; t < threads; ++t) {
    const std::size_t first = count * t / threads;
    const std::size_t last = count * (t + 1) / threads;
    pool.emplace_back([&body, first, last, t] { body(first, last, t); });
  }
}  // the jthreads join here

}  // namespace

JosephProjector::JosephProjector(std::span<const double> s_mm, std::span<const double> phi,
                                 std::size_t views, std::size_t bins, std::size_t n,
                                 double pixel_mm)
    : JosephProjector(s_mm, phi, views, bins, n, pixel_mm, Tof{}) {}

JosephProjector::JosephProjector(std::span<const double> s_mm, std::span<const double> phi,
                                 std::size_t views, std::size_t bins, std::size_t n,
                                 double pixel_mm, const Tof& tof)
    : s_(s_mm.begin(), s_mm.end()),
      phi_(phi.begin(), phi.end()),
      views_(views),
      bins_(bins),
      n_(n),
      pixel_mm_(pixel_mm),
      tof_(tof) {
  if (views == 0 || bins == 0 || s_mm.size() != views * bins || phi.size() != views * bins) {
    throw std::invalid_argument("JosephProjector: s_mm and phi must each hold views x bins = " +
                                std::to_string(views) + " x " + std::to_string(bins) +
                                " values, got " + std::to_string(s_mm.size()) + " and " +
                                std::to_string(phi.size()));
  }
  if (n == 0 || !(pixel_mm > 0.0) || !std::isfinite(pixel_mm)) {
    throw std::invalid_argument("JosephProjector: n must be positive and pixel_mm positive");
  }
  if (!std::all_of(s_.begin(), s_.end(), [](double v) { return std::isfinite(v); }) ||
      !std::all_of(phi_.begin(), phi_.end(), [](double v) { return std::isfinite(v); })) {
    throw std::invalid_argument("JosephProjector: s_mm and phi must be finite");
  }
  if (tof.bins == 0 ||
      (tof.bins > 1 && (!(tof.bin_ps > 0.0) || !(tof.ctr_fwhm_ps > 0.0) ||
                        !std::isfinite(tof.bin_ps) || !std::isfinite(tof.ctr_fwhm_ps)))) {
    throw std::invalid_argument(
        "JosephProjector: tof.bins must be positive, and with more than "
        "one bin the bin width and the resolution too");
  }
  if (tof.bins > 1) {
    // Bin j holds tau in [(j - K/2) w, (j + 1 - K/2) w); a point at t along the line has
    // tau = 2 t / c, so the edges along the line are c/2 times those.
    constexpr double c_mm_per_ps = 0.299792458;
    const auto k = static_cast<double>(tof.bins);
    tof_edges_mm_.resize(tof.bins + 1);
    for (std::size_t j = 0; j <= tof.bins; ++j) {
      tof_edges_mm_[j] = (static_cast<double>(j) - (k / 2.0)) * tof.bin_ps * c_mm_per_ps / 2.0;
    }
    tof_sigma_mm_ =
        tof.ctr_fwhm_ps / (2.0 * std::sqrt(2.0 * std::numbers::ln2)) * c_mm_per_ps / 2.0;
  }
  view_.resize(views);
  for (std::size_t v = 0; v < views; ++v) {
    double ax = 0.0;
    double ay = 0.0;
    for (std::size_t b = 0; b < bins; ++b) {
      ax += std::abs(std::sin(phi_[(v * bins) + b]));  // |dx|, the direction is (-sin, cos)
      ay += std::abs(std::cos(phi_[(v * bins) + b]));  // |dy|
    }
    view_[v].along_x = ax >= ay;
  }
}

// [snippet:walk]
// Calls visit(pixel_index, weight, t) for the up to 2 n pixels of one line, in step order; t is
// the step's position along the line, from the foot of its normal.
template <typename Visit>
void JosephProjector::walk(std::size_t view, std::size_t bin, const Visit& visit) const {
  const std::size_t i = (view * bins_) + bin;
  const double nx = std::cos(phi_[i]);
  const double ny = std::sin(phi_[i]);
  const double dx = -ny;
  const double dy = nx;
  const double s = s_[i];
  const bool along_x = view_[view].along_x;
  const double d_step = along_x ? dx : dy;  // the direction's component along the stepping axis
  const double d_other = along_x ? dy : dx;
  const double s_step = along_x ? s * nx : s * ny;
  const double s_other = along_x ? s * ny : s * nx;
  const double step = pixel_mm_ / std::abs(d_step);
  const double half = (static_cast<double>(n_) - 1.0) / 2.0;
  const auto size = static_cast<std::ptrdiff_t>(n_);
  // At step k the line is at center_k = (k - half) pixel_mm along the stepping axis, and at the
  // fractional pixel f_k = (s_other + t_k d_other) / pixel_mm + half across it, with
  // t_k = (center_k - s_step) / d_step. f_k is linear in k: f_k = f_0 + k df, no division per step.
  const double df = d_other / d_step;
  const double f0 =
      ((s_other + ((((-half * pixel_mm_) - s_step) / d_step) * d_other)) / pixel_mm_) + half;
  const double t0 = ((-half * pixel_mm_) - s_step) / d_step;
  const double dt = pixel_mm_ / d_step;
  for (std::ptrdiff_t k = 0; k < size; ++k) {
    const double f = f0 + (static_cast<double>(k) * df);  // fractional pixel
    const double t = t0 + (static_cast<double>(k) * dt);  // position along the line
    const double lo_f = std::floor(f);
    const double frac = f - lo_f;
    const auto lo = static_cast<std::ptrdiff_t>(lo_f);
    for (int j = 0; j < 2; ++j) {
      const std::ptrdiff_t o = lo + j;
      if (o < 0 || o >= size) {
        continue;  // outside the image: no weight
      }
      const double w = (j == 0 ? 1.0 - frac : frac) * step;
      const std::ptrdiff_t row = along_x ? o : k;
      const std::ptrdiff_t col = along_x ? k : o;
      visit(static_cast<std::size_t>((row * size) + col), w, t);
    }
  }
}
// [/snippet:walk]

// [snippet:kernel]
void JosephProjector::tof_kernel(double t, std::span<double> probability, std::size_t& first,
                                 std::size_t& last) const {
  const double reach = 6.0 * tof_sigma_mm_;
  const auto& e = tof_edges_mm_;
  // The bins that overlap [t - reach, t + reach]; outside them the probability is below 1e-9.
  first = static_cast<std::size_t>(std::upper_bound(e.begin() + 1, e.end(), t - reach) -
                                   (e.begin() + 1));
  last = static_cast<std::size_t>(std::lower_bound(e.begin(), e.end() - 1, t + reach) - e.begin());
  const double z = std::numbers::sqrt2 * tof_sigma_mm_;
  double below = std::erf((e[first] - t) / z);
  for (std::size_t j = first; j < last; ++j) {
    const double above = std::erf((e[j + 1] - t) / z);
    probability[j] = 0.5 * (above - below);
    below = above;
  }
}
// [/snippet:kernel]

void JosephProjector::check(std::span<const std::size_t> selected) const {
  for (const std::size_t v : selected) {
    if (v >= views_) {
      throw std::out_of_range("JosephProjector: view " + std::to_string(v) + " of " +
                              std::to_string(views_));
    }
  }
}

void JosephProjector::forward(std::span<const double> image, std::span<const std::size_t> selected,
                              std::span<double> out, unsigned threads) const {
  check(selected);
  const std::size_t k_tof = tof_.bins;
  if (image.size() != n_ * n_ || out.size() != selected.size() * bins_ * k_tof) {
    throw std::invalid_argument(
        "JosephProjector::forward: the image must hold n x n values and "
        "the output views x bins x TOF bins");
  }
  const std::size_t lines = selected.size() * bins_;
  parallel_chunks(
      lines, thread_count(threads, lines),
      [&](std::size_t first, std::size_t last, unsigned /*thread*/) {
        if (k_tof == 1) {
          for (std::size_t l = first; l < last; ++l) {
            double sum = 0.0;
            walk(selected[l / bins_], l % bins_,
                 [&](std::size_t p, double w, double /*t*/) { sum += image[p] * w; });
            out[l] = sum;
          }
          return;
        }
        // [snippet:tof-forward]
        std::vector<double> kernel(k_tof, 0.0);
        for (std::size_t l = first; l < last; ++l) {
          const std::span<double> line = out.subspan(l * k_tof, k_tof);
          std::fill(line.begin(), line.end(), 0.0);
          double at = std::numeric_limits<double>::quiet_NaN();  // the step whose kernel is held
          std::size_t lo = 0;
          std::size_t hi = 0;
          walk(selected[l / bins_], l % bins_, [&](std::size_t p, double w, double t) {
            if (t != at) {  // the two pixels of a step share its position, and so its kernel
              tof_kernel(t, kernel, lo, hi);
              at = t;
            }
            const double v = image[p] * w;
            for (std::size_t j = lo; j < hi; ++j) {
              line[j] += v * kernel[j];
            }
          });
        }
        // [/snippet:tof-forward]
      });
}

// [snippet:back]
void JosephProjector::back(std::span<const double> sino, std::span<const std::size_t> selected,
                           std::span<double> image, unsigned threads) const {
  check(selected);
  const std::size_t k_tof = tof_.bins;
  if (image.size() != n_ * n_ || sino.size() != selected.size() * bins_ * k_tof) {
    throw std::invalid_argument(
        "JosephProjector::back: the sinogram must hold views x bins x "
        "TOF bins values and the image n x n");
  }
  const std::size_t lines = selected.size() * bins_;
  const unsigned t = thread_count(threads, lines);
  // Two lines write to the same pixel, so the threads cannot share one image: each adds into
  // its own, and the images are summed afterwards in a fixed order.
  std::vector<std::vector<double>> partial(t, std::vector<double>(n_ * n_, 0.0));
  parallel_chunks(lines, t, [&](std::size_t first, std::size_t last, unsigned thread) {
    std::vector<double>& mine = partial[thread];
    std::vector<double> kernel(k_tof, 0.0);
    for (std::size_t l = first; l < last; ++l) {
      const std::span<const double> y = sino.subspan(l * k_tof, k_tof);
      if (std::all_of(y.begin(), y.end(), [](double v) { return v == 0.0; })) {
        continue;
      }
      if (k_tof == 1) {
        walk(selected[l / bins_], l % bins_,
             [&](std::size_t p, double w, double /*at*/) { mine[p] += w * y[0]; });
        continue;
      }
      double at = std::numeric_limits<double>::quiet_NaN();
      double value = 0.0;  // the line's TOF bins weighted by the held step's kernel
      walk(selected[l / bins_], l % bins_, [&](std::size_t p, double w, double pos) {
        if (pos != at) {
          std::size_t lo = 0;
          std::size_t hi = 0;
          tof_kernel(pos, kernel, lo, hi);
          value = 0.0;
          for (std::size_t j = lo; j < hi; ++j) {
            value += y[j] * kernel[j];
          }
          at = pos;
        }
        mine[p] += w * value;
      });
    }
  });
  std::fill(image.begin(), image.end(), 0.0);
  for (const auto& p : partial) {
    std::transform(image.begin(), image.end(), p.begin(), image.begin(), std::plus<>());
  }
}
// [/snippet:back]

}  // namespace recon
