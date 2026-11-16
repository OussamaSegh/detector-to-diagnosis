// SPDX-License-Identifier: MIT
// MiniDAQ - watching the scanner's time base during a run (Chapter 38, CR-0031).
//
// A coincidence compares two time stamps taken by two detector blocks. The timing calibration
// (Chapter 26) removes each crystal's fixed delay once; it cannot see a block whose time base moves
// during a run: a phase-locked loop that lost lock and locked again a few hundred picoseconds away,
// a board reset that restarted its counter, a reference that drifts. True coincidences between
// two blocks have a time difference whose mean depends only on the source and the geometry, so a
// change of that mean is a change of the blocks' clocks. The monitor measures it, interval by
// interval, from the coincidences the run produces anyway:
//
//   1. Per pair of blocks (a < b) it sums d = t_b - t_a of the prompt coincidences and of the
//      delayed ones, within +-half_window. The delayed pairs are randoms only; subtracting their
//      sums from the prompts' leaves the sums of the true coincidences, whose mean m_ab is not
//      diluted by the randoms.
//   2. The first `baseline_intervals` intervals give each pair its reference r_ab. Later intervals
//      give the shift s_ab = m_ab - r_ab, with its variance from the spread of d.
//   3. A shift of block b's clock by x moves every pair (a, b) by +x and every pair (b, c) by -x,
//      so the shifts of all pairs are explained by one offset per block: the weighted least squares
//      solution of s_ab = o_b - o_a. A common shift of all blocks moves no pair and cannot be seen;
//      the solution has a mean of zero over each group of blocks connected by pairs. A block in no
//      pair, or in a group of one, is unobserved.
//   4. chi2 / dof of that fit says whether the shifts are those of block clocks at all (about 1)
//      or something else, such as one pair of cables swapped.
//   5. A block whose |offset| is above a limit and above `significance` times its uncertainty is
//      at warning or alarm. The levels, the offsets and their history are what status() reports.
//
// record() and flush() are called by one thread, the pipeline's pair stage; snapshot() by any. The
// recording thread never waits: it publishes a finished interval with a try_lock and tries again
// at its next call if a reader holds the lock.
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <mutex>
#include <span>
#include <string>
#include <string_view>
#include <vector>

#include "minidaq/core/expected.hpp"
#include "minidaq/core/geometry.hpp"
#include "minidaq/core/single.hpp"

namespace minidaq {

// [snippet:config]
struct TimingMonitorConfig {
  Picoseconds interval{1'000'000'000'000};  // 1 s of acquisition time per evaluation
  std::uint32_t baseline_intervals = 2;     // the reference of each pair
  // Only time differences within +-half_window are used, prompts and delayeds alike. The trues of
  // a scanner of 300 mm are within about +-1 ns plus the resolution; each random adds noise in
  // proportion to the square of its difference, and the sorter's window is wider.
  Picoseconds half_window{2'000};
  // A pair with fewer true coincidences in an interval is not used. A scanner of 72 blocks at a
  // clinical rate gives each pair some tens of trues per second; the weights of the fit give a
  // pair with few of them little say.
  double min_trues = 10.0;
  double warning_ps = 100.0;  // assumption: confirm with team; a TOF scanner needs tighter limits
  double alarm_ps = 250.0;
  double significance = 5.0;  // and |offset| above this many standard deviations
  // The sorter's delayed window offset, which a delayed pair's time difference includes; set by
  // the pipeline from the sorter's configuration. 0: the sorter makes no delayed pairs.
  Picoseconds delay{0};
};
// [/snippet:config]

// The first problem of a configuration, or the configuration.
[[nodiscard]] Expected<TimingMonitorConfig, std::string> validate(const TimingMonitorConfig& c);

enum class TimingLevel : std::uint8_t { unobserved, normal, warning, alarm };
[[nodiscard]] std::string_view to_string(TimingLevel l) noexcept;

struct TimingBlock {
  TimingLevel level = TimingLevel::unobserved;
  double offset_ps = 0.0;  // in the latest evaluated interval, relative to the baseline
  double sigma_ps = 0.0;   // its standard deviation
  double worst_ps = 0.0;   // the offset of largest magnitude in any interval so far
  std::uint64_t alarm_intervals = 0;
  std::int64_t first_alarm_ps = -1;  // acquisition time of the end of the first interval at alarm
};

struct TimingSnapshot {
  std::uint64_t intervals = 0;  // intervals evaluated (the baseline ones included)
  bool baseline_done = false;
  std::uint32_t pairs = 0;    // pairs with a reference and enough trues in the latest interval
  std::uint32_t groups = 0;   // groups of connected, observed blocks in it
  double chi2_per_dof = 0.0;  // of its fit; 0 without degrees of freedom
  std::uint64_t alarm_intervals = 0;            // intervals with at least one block at alarm
  TimingLevel level = TimingLevel::unobserved;  // the worst block's level in the latest interval
  std::array<TimingBlock, ScannerGeometry::num_blocks> blocks{};
};

// [snippet:solve]
// One pair's measurement for the solver: the shift of the mean time difference t_b - t_a and its
// variance. a != b, both below `blocks`.
struct PairShift {
  std::uint32_t a = 0;
  std::uint32_t b = 0;
  double shift_ps = 0.0;
  double variance_ps2 = 0.0;
};

struct BlockOffsets {
  std::vector<double> offset_ps;  // per block; 0 for an unobserved block
  std::vector<double> sigma_ps;   // per block; 0 for an unobserved block
  std::vector<bool> observed;     // in a group of two or more blocks
  std::uint32_t groups = 0;
  double chi2 = 0.0;
  std::uint32_t dof = 0;
};

// The weighted least squares offsets o with s_ab = o_b - o_a for every pair, the mean of o zero
// over each connected group. Pairs with a variance that is not positive are ignored.
[[nodiscard]] BlockOffsets solve_block_offsets(std::size_t blocks,
                                               std::span<const PairShift> pairs);
// [/snippet:solve]

class TimingMonitor {
 public:
  static constexpr std::size_t blocks = ScannerGeometry::num_blocks;
  static constexpr std::size_t pairs = blocks * (blocks - 1) / 2;

  // Throws std::invalid_argument if validate(cfg) fails. Allocates; record() does not.
  explicit TimingMonitor(const TimingMonitorConfig& cfg = {});

  // Coincidences in time order of their first single, as the sorter emits them.
  void record(std::span<const Coincidence> found);
  // The end of the run: evaluates the interval in progress if its pairs have enough trues, and
  // publishes.
  void flush();
  [[nodiscard]] TimingSnapshot snapshot() const;
  [[nodiscard]] const TimingMonitorConfig& config() const noexcept { return cfg_; }

 private:
  struct Sums {
    double n_prompt = 0.0;
    double n_delayed = 0.0;
    double sum_prompt = 0.0;
    double sum_delayed = 0.0;
    double sq_prompt = 0.0;
    double sq_delayed = 0.0;
    void add(const Sums& o) noexcept;
  };
  void close_interval();
  void try_publish();
  static std::size_t pair_index(std::uint32_t a, std::uint32_t b) noexcept;

  TimingMonitorConfig cfg_;
  std::vector<Sums> current_;    // the interval in progress
  std::vector<Sums> reference_;  // the baseline intervals, summed
  std::vector<PairShift> shifts_;
  std::int64_t interval_end_ps_ = 0;
  bool started_ = false;
  TimingSnapshot state_;  // the recording thread's
  bool dirty_ = false;
  mutable std::mutex lock_;
  TimingSnapshot published_;  // under lock_
};

}  // namespace minidaq
