// SPDX-License-Identifier: MIT
// MiniDAQ - detector calibration: per-crystal energy and time corrections (Chapter 26).
//
// A front-end board reports, for each single, an 11-bit energy code and a time. Neither is right
// until it is calibrated: every crystal and SiPM has its own gain, the SiPM's response flattens at
// high energies, and every channel has its own delay. A CalibrationTable holds, per crystal,
//
//   energy_keV = a + b * c + q * c^2      c = the board's energy code (0 to 2047)
//   time       = time_reported - offset
//
// and applies both to a single. The identity table (a = 0, b = 0.5 keV, q = 0, offset 0) is what
// MiniDAQ did before Chapter 26: the code times the format's least significant bit.
//
// A table also says where it came from: an id and a version, the scanner it was measured on, when,
// until when it may be used, the temperature it was measured at and the procedure that made it.
// make() refuses a table whose coefficients are outside what a working detector can have, so a
// wrong file cannot turn a scanner's energies upside down; the procedure's own acceptance criteria
// (tools/calib) are stricter.
//
// PhotopeakMonitor watches a running acquisition: the mean calibrated energy of the singles near
// 511 keV, per detector block. A block whose mean moves away from 511 keV has drifted since the
// table was made (temperature, SiPM ageing, a bias that is not where it should be).
#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <vector>

#include "minidaq/core/cache.hpp"
#include "minidaq/core/expected.hpp"
#include "minidaq/core/geometry.hpp"
#include "minidaq/core/single.hpp"
#include "minidaq/format/packed_single.hpp"

namespace minidaq {

// [snippet:crystal]
struct CrystalCalibration {
  float a_kev = 0.0F;                    // energy at code 0
  float b_kev = packed::energy_lsb_kev;  // keV per code at code 0
  float q_kev = 0.0F;                    // curvature, keV per code squared
  std::int32_t time_offset_ps = 0;       // subtracted from the reported time

  friend bool operator==(const CrystalCalibration&, const CrystalCalibration&) = default;
};
// [/snippet:crystal]

// The limits make() enforces. A working detector's gain is within a factor of two of nominal, its
// response is monotonic over the whole code range and at most 40% below linear at the top, its
// pedestal is within 100 keV of zero and its channel delays within 5 ns (assumption: confirm with
// team; these bound a sane table, the procedure's acceptance criteria are tighter).
struct CalibrationLimits {
  float min_gain = 0.5F;  // b / 0.5 keV
  float max_gain = 2.0F;
  float max_abs_a_kev = 100.0F;
  float max_nonlinearity = 0.4F;  // -q * c_max^2 / (b * c_max) at c_max = 2047
  std::int32_t max_abs_time_offset_ps = 5'000;
};

struct CalibrationInfo {
  std::string id;             // e.g. "CAL-0001"
  std::uint32_t version = 0;  // grows by one with each new table of the same scanner
  std::string scanner_serial;
  std::string created_utc;      // YYYY-MM-DDTHH:MM:SSZ
  std::string valid_until_utc;  // YYYY-MM-DDTHH:MM:SSZ; the table is refused after it
  double reference_temperature_c = 25.0;
  std::string procedure;  // the calibration procedure and its version

  friend bool operator==(const CalibrationInfo&, const CalibrationInfo&) = default;
};

class CalibrationTable {
 public:
  // The table of a detector whose boards report calibrated energies: what MiniDAQ assumed before
  // Chapter 26. Its id is "identity" and it never expires.
  [[nodiscard]] static CalibrationTable identity();

  // Checks every entry against `limits` and returns the table, or one message per refused entry
  // (at most 20, then a count). `crystals` must have one entry per crystal of the scanner.
  [[nodiscard]] static Expected<CalibrationTable, std::vector<std::string>> make(
      CalibrationInfo info, std::vector<CrystalCalibration> crystals,
      const CalibrationLimits& limits = {});

  // [snippet:apply]
  // Corrects one single in place. A crystal outside the scanner is left as it is (the decoder
  // has already refused those).
  void apply(Single& s) const noexcept {
    const std::uint32_t i = s.crystal.value();
    if (i >= crystals_.size()) {
      return;
    }
    const CrystalCalibration& k = crystals_[i];
    const float c = s.energy.count() / packed::energy_lsb_kev;  // exact: the code times 0.5
    s.energy = KeV{k.a_kev + c * (k.b_kev + c * k.q_kev)};
    s.time = Picoseconds{s.time.count() - std::int64_t{k.time_offset_ps}};
  }
  // [/snippet:apply]
  void apply(std::span<Single> singles) const noexcept {
    for (Single& s : singles) {
      apply(s);
    }
  }

  [[nodiscard]] const CalibrationInfo& info() const noexcept { return info_; }
  [[nodiscard]] std::span<const CrystalCalibration> crystals() const noexcept { return crystals_; }
  [[nodiscard]] bool is_identity() const noexcept { return identity_; }
  // The largest offset minus the smallest: how far the correction can reorder two singles.
  [[nodiscard]] std::int64_t time_spread_ps() const noexcept { return spread_ps_; }
  // CRC-32 of the coefficients in their canonical byte order (canonical_bytes), which the file
  // carries so that a damaged or hand-edited table is refused.
  [[nodiscard]] std::uint32_t crc32() const noexcept { return crc_; }

 private:
  CalibrationTable() = default;
  CalibrationInfo info_;
  std::vector<CrystalCalibration> crystals_;
  std::int64_t spread_ps_ = 0;
  std::uint32_t crc_ = 0;
  bool identity_ = false;
};

// [snippet:canonical]
// The bytes the table's CRC-32 covers: for each crystal in order, a, b and q as IEEE 754 single
// precision and the offset as a two's complement 32-bit integer, all little-endian, 16 bytes per
// crystal. tools/calib writes the same bytes with struct.pack("<fffi", ...).
[[nodiscard]] std::vector<std::byte> canonical_bytes(std::span<const CrystalCalibration> crystals);
// [/snippet:canonical]

// True if `s` has the form YYYY-MM-DDTHH:MM:SSZ with a valid date and time. Times in that form
// compare correctly as strings.
[[nodiscard]] bool is_utc_timestamp(std::string_view s) noexcept;

// [snippet:monitor]
// The photopeak position per detector block, from the calibrated singles of a running
// acquisition. record() is called by one thread (the pipeline's decode stage); snapshot() by any.
class PhotopeakMonitor {
 public:
  static constexpr float window_lo_kev = 430.0F;  // the photopeak of 511 keV, +-80 keV:
  static constexpr float window_hi_kev = 590.0F;  // wider than its FWHM, narrower than Compton
  static constexpr std::size_t blocks = ScannerGeometry::num_blocks;

  struct Block {
    std::uint64_t singles = 0;  // in the window, since the start
    double mean_kev = 0.0;      // their mean energy (0 if none)
  };

  void record(std::span<const Single> singles) noexcept;
  [[nodiscard]] std::array<Block, blocks> snapshot() const noexcept;
  void reset() noexcept;

 private:
  struct alignas(cache_line_size) Counter {
    std::atomic<std::uint64_t> n{0};
    std::atomic<double> sum_kev{0.0};
  };
  std::array<Counter, blocks> counters_{};
};
// [/snippet:monitor]

}  // namespace minidaq
