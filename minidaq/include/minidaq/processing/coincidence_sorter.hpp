// SPDX-License-Identifier: MIT
// MiniDAQ - the streaming coincidence sorter (Chapter 10).
//
// Input: singles in time order (TimeOrder), in chunks of any size. Output:
// prompt coincidences, and optionally delayed coincidences for the randoms
// estimate. The sorter is a pure function of its input: the same singles give
// the same coincidences however the input is cut into chunks, which is what
// lets the tests compare it with a reference and lets Exercise 10.3 split the
// work across threads.
//
// Order of operations for each single:
//   1. Energy gate: outside [energy_low, energy_high] keV, counted and dropped.
//   2. Order check: a single earlier than the previous one is counted and
//      dropped (the sorter cannot reopen windows it has closed).
//   3. Windowing: see WindowMode. A window's singles form a group: two singles
//      are a candidate pair, three or more are a multiple, resolved by the
//      MultiplesPolicy.
//   4. Geometry: a pair is "good" if its crystals are in sectors at least
//      min_sector_difference apart and, if fov_radius_mm > 0, its line of
//      response passes within fov_radius_mm of the scanner axis.
//   5. Delayed window: each window's opener also opens a window of the same
//      width, delay_ps later. Its singles cannot come from the same decay as
//      the opener, so its pairs count randoms only (CoincidenceKind::delayed).
#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <string_view>
#include <vector>

#include "minidaq/core/expected.hpp"
#include "minidaq/core/single.hpp"

namespace minidaq {

// [snippet:modes]
enum class WindowMode : std::uint8_t {
  // The first single not yet in a window opens one; every single up to
  // window_ps later joins it; the next window opens at the first single after
  // the group. Each single belongs to exactly one window (non-paralysable).
  fixed,
  // Every single opens its own window and is paired with the singles up to
  // window_ps after it: the window's pairs are (opener, later single), so
  // each pair is considered once, in the window of its earlier single. A
  // single can be in several windows, so b-c can be a clean pair in b's window
  // while c also makes a with b a multiple in a's.
  per_single,
};

// What to do with a window that holds three or more singles. The names follow
// the GATE coincidence sorter's policies (verify: against the GATE version in
// use; GATE has more variants than these four).
enum class MultiplesPolicy : std::uint8_t {
  kill_all,               // discard the whole window
  take_all_goods,         // keep every good pair in the window
  take_winner_of_goods,   // keep the good pair with the highest summed energy
  keep_if_only_one_good,  // keep the good pair if exactly one pair is good
};
// [/snippet:modes]

[[nodiscard]] std::string_view to_string(WindowMode m) noexcept;
[[nodiscard]] std::string_view to_string(MultiplesPolicy p) noexcept;
[[nodiscard]] Expected<WindowMode, std::string> parse_window_mode(std::string_view s);
[[nodiscard]] Expected<MultiplesPolicy, std::string> parse_multiples_policy(std::string_view s);

// [snippet:config]
struct SorterConfig {
  Picoseconds window{4'000};  // a partner at most this much later (inclusive)
  // Delayed window offset; 0 disables the delayed window. Must be well above
  // the window and any time correlation in the data (the default is 25 times
  // the window).
  Picoseconds delay{100'000};
  WindowMode mode = WindowMode::fixed;
  MultiplesPolicy multiples = MultiplesPolicy::kill_all;
  // assumption: confirm with team. A common 511 keV window for LYSO.
  double energy_low_kev = 435.0;
  double energy_high_kev = 585.0;
  // Sectors are the transaxial blocks of ScannerGeometry (24 around the ring).
  // 1 rejects pairs within one block; 0 accepts everything.
  std::uint32_t min_sector_difference = 1;
  double fov_radius_mm = 0.0;  // 0: no field-of-view cut
};
// [/snippet:config]

// Checks a configuration; the message names the first problem found.
[[nodiscard]] Expected<SorterConfig, std::string> validate(const SorterConfig& cfg);

// [snippet:stats]
// Every single that enters is accounted for: in fixed mode,
//   singles_in = energy_rejected + out_of_order + singles_alone
//                + 2 * pair_windows + singles_in_multiples.
struct SorterStats {
  std::uint64_t singles_in = 0;
  std::uint64_t energy_rejected = 0;
  std::uint64_t out_of_order = 0;
  std::uint64_t singles_alone = 0;         // windows with one single
  std::uint64_t pair_windows = 0;          // windows with exactly two singles
  std::uint64_t multiple_windows = 0;      // windows with three or more
  std::uint64_t singles_in_multiples = 0;
  std::uint64_t geometry_rejected = 0;     // candidate pairs that were not good
  std::uint64_t prompts = 0;               // prompt coincidences emitted
  std::uint64_t prompts_from_multiples = 0;
  std::uint64_t delayed = 0;               // delayed coincidences emitted
  friend bool operator==(const SorterStats&, const SorterStats&) = default;
};
// [/snippet:stats]

class CoincidenceSorter {
 public:
  // Throws std::invalid_argument if validate(cfg) fails.
  explicit CoincidenceSorter(const SorterConfig& cfg);

  // Sorts `in` and appends the coincidences it completes to `out`. Windows
  // close only once a later single proves them complete, so the last
  // coincidences of a run come from flush().
  void push(std::span<const Single> in, std::vector<Coincidence>& out);
  // Closes every open window, as at the end of a run, and starts afresh.
  void flush(std::vector<Coincidence>& out);

  [[nodiscard]] const SorterStats& stats() const noexcept { return stats_; }
  // Singles held, waiting for their windows to complete.
  [[nodiscard]] std::size_t held() const noexcept { return buf_.size() - first_; }
  // Time of the oldest single held; only meaningful while held() > 0.
  [[nodiscard]] Picoseconds oldest_held_time() const noexcept { return buf_[first_].time; }

  // Is the pair good? Exposed for tests and for Exercise 10.2.
  [[nodiscard]] bool good(const Single& a, const Single& b) const noexcept;

 private:
  void accept(const Single& s, std::vector<Coincidence>& out);
  void close_ready(Picoseconds now, std::vector<Coincidence>& out);
  void close_window(std::vector<Coincidence>& out);
  void resolve_prompts(std::size_t begin, std::size_t end, std::vector<Coincidence>& out);
  void resolve_delayed(std::size_t opener, std::size_t begin, std::size_t end, std::vector<Coincidence>& out);
  void compact();

  SorterConfig cfg_;
  Picoseconds horizon_;            // a window is complete once data this much later has arrived
  double fov_r2_ = 0.0;            // fov_radius_mm squared, 0 for no cut
  std::vector<Single> buf_;        // accepted singles; [first_, size) are still needed
  std::size_t first_ = 0;          // oldest single still needed
  std::size_t opener_ = 0;         // next single to open a window
  std::size_t delayed_begin_ = 0;  // first single that can be in the next delayed window
  bool have_last_ = false;
  Picoseconds last_time_{};
  SorterStats stats_{};
};

}  // namespace minidaq
