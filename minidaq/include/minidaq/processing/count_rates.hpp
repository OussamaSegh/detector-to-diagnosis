// SPDX-License-Identifier: MIT
// MiniDAQ - count-rate figures of merit (Chapter 11).
//
// Rates are per second. Trues, scatters and randoms are what the prompts
// contain; with ground truth they are counted directly, on a real scanner they
// are estimated (randoms from the delayed window or the singles, scatters from
// a fit to the tails of the projection outside the object, as NEMA NU 2 does).
#pragma once

namespace minidaq {

// [snippet:rates]
struct CountRates {
  double trues = 0.0;
  double scatters = 0.0;
  double randoms = 0.0;

  [[nodiscard]] constexpr double prompts() const noexcept { return trues + scatters + randoms; }

  // Scatter fraction: the share of scatters among the coincidences from one
  // decay. Randoms are left out, so it does not depend on the activity until
  // dead time and pile-up change the spectrum.
  [[nodiscard]] constexpr double scatter_fraction() const noexcept {
    return trues + scatters > 0.0 ? scatters / (trues + scatters) : 0.0;
  }

  // Noise-equivalent count rate, NECR = T^2 / (T + S + k R): the rate of a
  // noise-free (trues only) acquisition that would give the same signal to
  // noise ratio. k = 2 when randoms are subtracted with a delayed window,
  // whose counts are as noisy as the randoms themselves; k = 1 when the
  // randoms estimate is smooth (from the singles, or a variance-reduced
  // delayed estimate). (verify: the k convention of the NEMA NU 2 edition in
  // use.)
  [[nodiscard]] constexpr double necr(double k) const noexcept {
    const double d = trues + scatters + k * randoms;
    return d > 0.0 ? trues * trues / d : 0.0;
  }
};
// [/snippet:rates]

}  // namespace minidaq
