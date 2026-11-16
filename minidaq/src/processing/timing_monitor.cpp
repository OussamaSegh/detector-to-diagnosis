// SPDX-License-Identifier: MIT
#include "minidaq/processing/timing_monitor.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <utility>

namespace minidaq {

Expected<TimingMonitorConfig, std::string> validate(const TimingMonitorConfig& c) {
  if (c.interval.count() <= 0) {
    return Unexpected{std::string{"interval must be positive"}};
  }
  if (c.baseline_intervals == 0) {
    return Unexpected{std::string{"baseline_intervals must be at least 1"}};
  }
  if (!(c.min_trues >= 1.0)) {
    return Unexpected{std::string{"min_trues must be at least 1"}};
  }
  if (!(c.warning_ps > 0.0) || !(c.alarm_ps >= c.warning_ps)) {
    return Unexpected{std::string{"the limits must be 0 < warning_ps <= alarm_ps"}};
  }
  if (!(c.significance >= 0.0)) {
    return Unexpected{std::string{"significance must not be negative"}};
  }
  if (c.half_window.count() <= 0) {
    return Unexpected{std::string{"half_window must be positive"}};
  }
  if (c.delay.count() < 0) {
    return Unexpected{std::string{"delay must not be negative"}};
  }
  return c;
}

std::string_view to_string(TimingLevel l) noexcept {
  switch (l) {
    case TimingLevel::unobserved:
      return "unobserved";
    case TimingLevel::normal:
      return "normal";
    case TimingLevel::warning:
      return "warning";
    case TimingLevel::alarm:
      return "alarm";
  }
  return "unobserved";
}

// [snippet:solver]
BlockOffsets solve_block_offsets(std::size_t blocks, std::span<const PairShift> pairs) {
  BlockOffsets out;
  out.offset_ps.assign(blocks, 0.0);
  out.sigma_ps.assign(blocks, 0.0);
  out.observed.assign(blocks, false);
  // The normal equations L o = r of the weighted fit: L is the graph's Laplacian with weights
  // 1 / variance, r collects the weighted shifts.
  std::vector<double> L(blocks * blocks, 0.0);
  std::vector<double> r(blocks, 0.0);
  std::vector<std::size_t> group(blocks);
  for (std::size_t i = 0; i < blocks; ++i) {
    group[i] = i;
  }
  const auto root = [&](std::size_t i) {
    while (group[i] != i) {
      i = group[i] = group[group[i]];
    }
    return i;
  };
  std::size_t used = 0;
  for (const PairShift& p : pairs) {
    if (!(p.variance_ps2 > 0.0) || p.a == p.b || p.a >= blocks || p.b >= blocks) {
      continue;
    }
    const double w = 1.0 / p.variance_ps2;
    L[p.a * blocks + p.a] += w;
    L[p.b * blocks + p.b] += w;
    L[p.a * blocks + p.b] -= w;
    L[p.b * blocks + p.a] -= w;
    r[p.b] += w * p.shift_ps;
    r[p.a] -= w * p.shift_ps;
    group[root(p.a)] = root(p.b);
    ++used;
  }
  // L is singular: adding the same value to every offset of a group changes nothing. Adding
  // J / n for each group (J all ones over the group's blocks) makes it invertible without
  // changing the solution of mean zero; (L + J/n)^-1 - J/n is then the covariance of the offsets.
  std::vector<std::size_t> size(blocks, 0);
  for (std::size_t i = 0; i < blocks; ++i) {
    ++size[root(i)];
  }
  std::vector<double> M = L;
  for (std::size_t i = 0; i < blocks; ++i) {
    for (std::size_t j = 0; j < blocks; ++j) {
      if (root(i) == root(j)) {
        M[i * blocks + j] += 1.0 / static_cast<double>(size[root(i)]);
      }
    }
  }
  // Gauss-Jordan inversion with partial pivoting; M is symmetric positive definite.
  std::vector<double> inv(blocks * blocks, 0.0);
  for (std::size_t i = 0; i < blocks; ++i) {
    inv[i * blocks + i] = 1.0;
  }
  for (std::size_t c = 0; c < blocks; ++c) {
    std::size_t pivot = c;
    for (std::size_t i = c + 1; i < blocks; ++i) {
      if (std::abs(M[i * blocks + c]) > std::abs(M[pivot * blocks + c])) {
        pivot = i;
      }
    }
    if (pivot != c) {
      for (std::size_t j = 0; j < blocks; ++j) {
        std::swap(M[c * blocks + j], M[pivot * blocks + j]);
        std::swap(inv[c * blocks + j], inv[pivot * blocks + j]);
      }
    }
    const double d = M[c * blocks + c];
    for (std::size_t j = 0; j < blocks; ++j) {
      M[c * blocks + j] /= d;
      inv[c * blocks + j] /= d;
    }
    for (std::size_t i = 0; i < blocks; ++i) {
      if (i != c) {
        const double f = M[i * blocks + c];
        if (f != 0.0) {
          for (std::size_t j = 0; j < blocks; ++j) {
            M[i * blocks + j] -= f * M[c * blocks + j];
            inv[i * blocks + j] -= f * inv[c * blocks + j];
          }
        }
      }
    }
  }
  std::size_t groups = 0;
  std::size_t observed = 0;
  for (std::size_t i = 0; i < blocks; ++i) {
    if (root(i) == i && size[i] >= 2) {
      ++groups;
    }
  }
  for (std::size_t i = 0; i < blocks; ++i) {
    if (size[root(i)] < 2) {
      continue;  // in no pair: unobserved
    }
    out.observed[i] = true;
    ++observed;
    double o = 0.0;
    for (std::size_t j = 0; j < blocks; ++j) {
      o += inv[i * blocks + j] * r[j];
    }
    out.offset_ps[i] = o;
    const double var = inv[i * blocks + i] - 1.0 / static_cast<double>(size[root(i)]);
    out.sigma_ps[i] = std::sqrt(std::max(var, 0.0));
  }
  for (const PairShift& p : pairs) {
    if (!(p.variance_ps2 > 0.0) || p.a == p.b || p.a >= blocks || p.b >= blocks) {
      continue;
    }
    const double e = p.shift_ps - (out.offset_ps[p.b] - out.offset_ps[p.a]);
    out.chi2 += e * e / p.variance_ps2;
  }
  out.groups = static_cast<std::uint32_t>(groups);
  // Each group fixes its blocks' offsets up to one common value.
  const std::size_t unknowns = observed - groups;
  out.dof = used > unknowns ? static_cast<std::uint32_t>(used - unknowns) : 0;
  return out;
}
// [/snippet:solver]

void TimingMonitor::Sums::add(const Sums& o) noexcept {
  n_prompt += o.n_prompt;
  n_delayed += o.n_delayed;
  sum_prompt += o.sum_prompt;
  sum_delayed += o.sum_delayed;
  sq_prompt += o.sq_prompt;
  sq_delayed += o.sq_delayed;
}

TimingMonitor::TimingMonitor(const TimingMonitorConfig& cfg)
    : cfg_{cfg}, current_(pairs), reference_(pairs) {
  if (auto ok = validate(cfg); !ok) {
    throw std::invalid_argument("timing monitor: " + ok.error());
  }
  shifts_.reserve(pairs);
}

std::size_t TimingMonitor::pair_index(std::uint32_t a, std::uint32_t b) noexcept {
  // a < b: the pairs of row a start after the a rows above it, of blocks - 1, blocks - 2, ...
  return a * (2 * blocks - a - 1) / 2 + (b - a - 1);
}

// [snippet:record]
void TimingMonitor::record(std::span<const Coincidence> found) {
  for (const Coincidence& c : found) {
    const std::int64_t t = c.first.time.count();
    if (!started_) {
      interval_end_ps_ = t + cfg_.interval.count();
      started_ = true;
    }
    while (t >= interval_end_ps_) {
      close_interval();
      interval_end_ps_ += cfg_.interval.count();
    }
    if (!ScannerGeometry::valid(c.first.crystal) || !ScannerGeometry::valid(c.second.crystal)) {
      continue;
    }
    std::uint32_t a = ScannerGeometry::block_of(c.first.crystal);
    std::uint32_t b = ScannerGeometry::block_of(c.second.crystal);
    if (a == b) {
      continue;
    }
    const bool delayed = c.kind == CoincidenceKind::delayed;
    // t_second - t_first, without the delayed window's offset: the same range for both kinds.
    double d =
        static_cast<double>(c.time_difference().count() - (delayed ? cfg_.delay.count() : 0));
    if (a > b) {
      std::swap(a, b);
      d = -d;  // t_b - t_a with a < b
    }
    if (std::abs(d) > static_cast<double>(cfg_.half_window.count())) {
      continue;
    }
    Sums& s = current_[pair_index(a, b)];
    if (delayed) {
      s.n_delayed += 1.0;
      s.sum_delayed += d;
      s.sq_delayed += d * d;
    } else {
      s.n_prompt += 1.0;
      s.sum_prompt += d;
      s.sq_prompt += d * d;
    }
  }
  try_publish();
}
// [/snippet:record]

void TimingMonitor::flush() {
  // The interval in progress counts only if one of its pairs has enough trues: a run that ends
  // just after an interval closed must not report its blocks unobserved.
  const bool enough = std::ranges::any_of(
      current_, [&](const Sums& s) { return s.n_prompt - s.n_delayed >= cfg_.min_trues; });
  if (started_ && enough) {
    close_interval();
  }
  started_ = false;
  dirty_ = true;
  const std::lock_guard<std::mutex> hold{lock_};
  published_ = state_;
  dirty_ = false;
}

// [snippet:close]
void TimingMonitor::close_interval() {
  const bool baseline = state_.intervals < cfg_.baseline_intervals;
  ++state_.intervals;
  if (baseline) {
    for (std::size_t i = 0; i < pairs; ++i) {
      reference_[i].add(current_[i]);
      current_[i] = Sums{};
    }
    state_.baseline_done = state_.intervals == cfg_.baseline_intervals;
    dirty_ = true;
    return;
  }
  // The mean of the trues' time differences and its variance: m = (S_p - S_d) / (n_p - n_d), and,
  // for counts that are Poisson, var(m) = (sum over prompts and delayeds of (d - m)^2) / n^2.
  const auto mean_and_variance = [](const Sums& s, double min_trues, double& m, double& v) {
    const double n = s.n_prompt - s.n_delayed;
    if (n < min_trues) {
      return false;
    }
    m = (s.sum_prompt - s.sum_delayed) / n;
    const double spread = (s.sq_prompt + s.sq_delayed) - 2.0 * m * (s.sum_prompt + s.sum_delayed) +
                          m * m * (s.n_prompt + s.n_delayed);
    v = spread / (n * n);
    return v > 0.0;
  };
  shifts_.clear();
  std::size_t i = 0;
  for (std::uint32_t a = 0; a < blocks; ++a) {
    for (std::uint32_t b = a + 1; b < blocks; ++b, ++i) {
      double m = 0.0;
      double v = 0.0;
      double ref = 0.0;
      double ref_v = 0.0;
      if (mean_and_variance(current_[i], cfg_.min_trues, m, v) &&
          mean_and_variance(reference_[i], cfg_.min_trues, ref, ref_v)) {
        shifts_.push_back(PairShift{a, b, m - ref, v + ref_v});
      }
      current_[i] = Sums{};
    }
  }
  const BlockOffsets fit = solve_block_offsets(blocks, shifts_);
  state_.pairs = static_cast<std::uint32_t>(shifts_.size());
  state_.groups = fit.groups;
  state_.chi2_per_dof = fit.dof > 0 ? fit.chi2 / fit.dof : 0.0;
  TimingLevel worst = TimingLevel::unobserved;
  bool any_alarm = false;
  for (std::size_t k = 0; k < blocks; ++k) {
    TimingBlock& blk = state_.blocks[k];
    if (!fit.observed[k]) {
      blk.level = TimingLevel::unobserved;
      continue;
    }
    blk.offset_ps = fit.offset_ps[k];
    blk.sigma_ps = fit.sigma_ps[k];
    const double mag = std::abs(blk.offset_ps);
    if (mag > std::abs(blk.worst_ps)) {
      blk.worst_ps = blk.offset_ps;
    }
    const bool significant = mag > cfg_.significance * blk.sigma_ps;
    blk.level = !significant            ? TimingLevel::normal
                : mag > cfg_.alarm_ps   ? TimingLevel::alarm
                : mag > cfg_.warning_ps ? TimingLevel::warning
                                        : TimingLevel::normal;
    if (blk.level == TimingLevel::alarm) {
      ++blk.alarm_intervals;
      if (blk.first_alarm_ps < 0) {
        blk.first_alarm_ps = interval_end_ps_;
      }
      any_alarm = true;
    }
    worst = std::max(worst, blk.level);
  }
  if (any_alarm) {
    ++state_.alarm_intervals;
  }
  state_.level = worst;
  dirty_ = true;
}
// [/snippet:close]

void TimingMonitor::try_publish() {
  if (!dirty_) {
    return;
  }
  // Never wait for a reader: if one holds the lock, the next call publishes.
  std::unique_lock<std::mutex> hold{lock_, std::try_to_lock};
  if (hold.owns_lock()) {
    published_ = state_;
    dirty_ = false;
  }
}

TimingSnapshot TimingMonitor::snapshot() const {
  const std::lock_guard<std::mutex> hold{lock_};
  return published_;
}

}  // namespace minidaq
