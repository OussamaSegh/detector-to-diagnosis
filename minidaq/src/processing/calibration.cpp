// SPDX-License-Identifier: MIT
// MiniDAQ - detector calibration (Chapter 26).
#include "minidaq/processing/calibration.hpp"

#include <algorithm>
#include <bit>
#include <cmath>
#include <cstring>
#include <string_view>

#include "minidaq/core/crc32.hpp"

namespace minidaq {

namespace {

constexpr float max_code = static_cast<float>(packed::energy_mask);  // 2047

void put32(std::vector<std::byte>& out, std::uint32_t v) {
  for (int k = 0; k < 4; ++k) {
    out.push_back(static_cast<std::byte>((v >> (8 * k)) & 0xFFU));
  }
}

std::string where(std::size_t i) { return "crystal " + std::to_string(i) + ": "; }

// [snippet:check]
// What is wrong with one crystal's entry, or "" if nothing.
std::string check_entry(const CrystalCalibration& k, const CalibrationLimits& lim) {
  if (!std::isfinite(k.a_kev) || !std::isfinite(k.b_kev) || !std::isfinite(k.q_kev)) {
    return "a coefficient is not a finite number";
  }
  const float gain = k.b_kev / packed::energy_lsb_kev;
  if (gain < lim.min_gain || gain > lim.max_gain) {  // finite: checked above
    return "gain " + std::to_string(gain) + " is outside " + std::to_string(lim.min_gain) + " to " +
           std::to_string(lim.max_gain);
  }
  if (std::abs(k.a_kev) > lim.max_abs_a_kev) {
    return "energy at code 0 is " + std::to_string(k.a_kev) + " keV";
  }
  // Monotonic over the whole range: the slope b + 2 q c stays positive up to the last code.
  if (k.b_kev + 2.0F * k.q_kev * max_code <= 0.0F) {
    return "energy falls with the code before code 2047";
  }
  // Curvature bounded both ways: at most max_nonlinearity of the linear term at the top.
  if (std::abs(k.q_kev) * max_code > lim.max_nonlinearity * k.b_kev) {
    return "nonlinearity is more than " + std::to_string(lim.max_nonlinearity) + " at code 2047";
  }
  if (k.time_offset_ps < -lim.max_abs_time_offset_ps ||
      k.time_offset_ps > lim.max_abs_time_offset_ps) {
    return "time offset " + std::to_string(k.time_offset_ps) + " ps is beyond +-" +
           std::to_string(lim.max_abs_time_offset_ps) + " ps";
  }
  return {};
}
// [/snippet:check]

bool digits(std::string_view s, std::size_t at, std::size_t n, int& out) {
  out = 0;
  for (std::size_t i = at; i < at + n; ++i) {
    if (s[i] < '0' || s[i] > '9') {
      return false;
    }
    out = out * 10 + (s[i] - '0');
  }
  return true;
}

}  // namespace

CalibrationTable CalibrationTable::identity() {
  CalibrationTable t;
  t.info_.id = "identity";
  t.info_.version = 0;
  t.info_.procedure = "none: the boards report calibrated energies";
  t.info_.valid_until_utc = "9999-12-31T23:59:59Z";
  t.crystals_.assign(ScannerGeometry::num_crystals, CrystalCalibration{});
  t.crc_ = minidaq::crc32(canonical_bytes(t.crystals_));
  t.identity_ = true;
  return t;
}

Expected<CalibrationTable, std::vector<std::string>> CalibrationTable::make(
    CalibrationInfo info, std::vector<CrystalCalibration> crystals,
    const CalibrationLimits& limits) {
  constexpr std::size_t max_messages = 20;
  std::vector<std::string> errors;
  if (crystals.size() != ScannerGeometry::num_crystals) {
    errors.push_back("the table has " + std::to_string(crystals.size()) +
                     " crystals, the scanner " + std::to_string(ScannerGeometry::num_crystals));
    return Unexpected{std::move(errors)};
  }
  std::size_t refused = 0;
  for (std::size_t i = 0; i < crystals.size(); ++i) {
    if (const std::string why = check_entry(crystals[i], limits); !why.empty()) {
      if (++refused <= max_messages) {
        errors.push_back(where(i) + why);
      }
    }
  }
  if (refused > max_messages) {
    errors.push_back("and " + std::to_string(refused - max_messages) + " more crystals");
  }
  if (!is_utc_timestamp(info.created_utc)) {
    errors.push_back("created_utc '" + info.created_utc + "' is not YYYY-MM-DDTHH:MM:SSZ");
  }
  if (!is_utc_timestamp(info.valid_until_utc)) {
    errors.push_back("valid_until_utc '" + info.valid_until_utc + "' is not YYYY-MM-DDTHH:MM:SSZ");
  } else if (is_utc_timestamp(info.created_utc) && info.valid_until_utc <= info.created_utc) {
    errors.emplace_back("valid_until_utc is not after created_utc");
  }
  if (info.id.empty() || info.scanner_serial.empty() || info.procedure.empty()) {
    errors.emplace_back("id, scanner_serial and procedure must not be empty");
  }
  if (!std::isfinite(info.reference_temperature_c) || info.reference_temperature_c < -40.0 ||
      info.reference_temperature_c > 125.0) {
    errors.emplace_back("reference_temperature_c is outside -40 to 125");
  }
  if (!errors.empty()) {
    return Unexpected{std::move(errors)};
  }
  CalibrationTable t;
  t.info_ = std::move(info);
  t.crystals_ = std::move(crystals);
  const auto [lo, hi] =
      std::ranges::minmax_element(t.crystals_, {}, &CrystalCalibration::time_offset_ps);
  t.spread_ps_ = std::int64_t{hi->time_offset_ps} - lo->time_offset_ps;
  t.crc_ = minidaq::crc32(canonical_bytes(t.crystals_));
  return t;
}

std::vector<std::byte> canonical_bytes(std::span<const CrystalCalibration> crystals) {
  std::vector<std::byte> out;
  out.reserve(crystals.size() * 16);
  for (const CrystalCalibration& k : crystals) {
    put32(out, std::bit_cast<std::uint32_t>(k.a_kev));
    put32(out, std::bit_cast<std::uint32_t>(k.b_kev));
    put32(out, std::bit_cast<std::uint32_t>(k.q_kev));
    put32(out, std::bit_cast<std::uint32_t>(k.time_offset_ps));
  }
  return out;
}

bool is_utc_timestamp(std::string_view s) noexcept {
  // 0123456789012345678 9
  // YYYY-MM-DDTHH:MM:SSZ
  if (s.size() != 20 || s[4] != '-' || s[7] != '-' || s[10] != 'T' || s[13] != ':' ||
      s[16] != ':' || s[19] != 'Z') {
    return false;
  }
  int y = 0;
  int mo = 0;
  int d = 0;
  int h = 0;
  int mi = 0;
  int sec = 0;
  if (!digits(s, 0, 4, y) || !digits(s, 5, 2, mo) || !digits(s, 8, 2, d) || !digits(s, 11, 2, h) ||
      !digits(s, 14, 2, mi) || !digits(s, 17, 2, sec)) {
    return false;
  }
  static constexpr std::array<int, 12> days{31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
  if (mo < 1 || mo > 12 || d < 1 || d > days[static_cast<std::size_t>(mo - 1)]) {
    return false;
  }
  const bool leap = (y % 4 == 0 && y % 100 != 0) || y % 400 == 0;
  if (mo == 2 && d == 29 && !leap) {
    return false;
  }
  return h <= 23 && mi <= 59 && sec <= 59;  // no leap seconds in table timestamps
}

void PhotopeakMonitor::record(std::span<const Single> singles) noexcept {
  std::array<std::uint64_t, blocks> n{};
  std::array<double, blocks> sum{};
  for (const Single& s : singles) {
    const float e = s.energy.count();
    if (e >= window_lo_kev && e <= window_hi_kev && ScannerGeometry::valid(s.crystal)) {
      const std::uint32_t b = ScannerGeometry::block_of(s.crystal);
      ++n[b];
      sum[b] += static_cast<double>(e);
    }
  }
  // One writer: a load and a store, not a read-modify-write, per block with data.
  for (std::size_t b = 0; b < blocks; ++b) {
    if (n[b] != 0) {
      Counter& c = counters_[b];
      c.sum_kev.store(c.sum_kev.load(std::memory_order_relaxed) + sum[b],
                      std::memory_order_relaxed);
      c.n.store(c.n.load(std::memory_order_relaxed) + n[b], std::memory_order_release);
    }
  }
}

std::array<PhotopeakMonitor::Block, PhotopeakMonitor::blocks> PhotopeakMonitor::snapshot()
    const noexcept {
  std::array<Block, blocks> out{};
  for (std::size_t b = 0; b < blocks; ++b) {
    const std::uint64_t n = counters_[b].n.load(std::memory_order_acquire);
    const double sum = counters_[b].sum_kev.load(std::memory_order_relaxed);
    out[b].singles = n;
    out[b].mean_kev = n == 0 ? 0.0 : sum / static_cast<double>(n);
  }
  return out;
}

void PhotopeakMonitor::reset() noexcept {
  for (Counter& c : counters_) {
    c.n.store(0, std::memory_order_relaxed);
    c.sum_kev.store(0.0, std::memory_order_relaxed);
  }
}

}  // namespace minidaq
