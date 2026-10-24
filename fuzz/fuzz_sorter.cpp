// SPDX-License-Identifier: MIT
// Fuzz target: the coincidence sorter and the stream merger (Chapter 10).
//
// The first four bytes choose a configuration (window mode, multiples policy,
// delayed window, field-of-view cut, sector cut, window width, where to split
// the input, number of boards); every following four bytes are one single
// (time step, crystal, energy, ring). Properties checked for any input:
//  - the sorter's output and counters do not depend on how the input is split;
//  - in fixed mode every single is in exactly one window (the SorterStats sum);
//  - every prompt is within the window, every delayed pair within
//    [delay, delay + window], and every pair passes the geometry cuts;
//  - merging the singles from several boards gives back exactly the input
//    times, in order, with nothing late when the merger may wait.
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <span>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/processing/coincidence_sorter.hpp"
#include "minidaq/processing/stream_merger.hpp"

using namespace minidaq;

namespace {

void check(bool ok) {
  if (!ok) {
    std::abort();  // libFuzzer reports the input that got here
  }
}

std::vector<Coincidence> sort_in_two(const SorterConfig& c, std::span<const Single> in, std::size_t split,
                                     SorterStats& st) {
  CoincidenceSorter s{c};
  std::vector<Coincidence> out;
  s.push(in.first(split), out);
  s.push(in.subspan(split), out);
  s.flush(out);
  st = s.stats();
  return out;
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data, std::size_t size) {
  if (size < 4) {
    return 0;
  }
  SorterConfig c;
  c.mode = (data[0] & 1U) != 0 ? WindowMode::per_single : WindowMode::fixed;
  c.multiples = static_cast<MultiplesPolicy>((data[0] >> 1U) & 3U);
  c.window = Picoseconds{(static_cast<std::int64_t>(data[1]) + 1) * 100};  // 0.1 to 25.6 ns
  c.delay = (data[0] & 8U) != 0 ? c.window * 4 : Picoseconds{0};
  c.fov_radius_mm = (data[0] & 16U) != 0 ? 110.0 : 0.0;
  c.min_sector_difference = data[0] >> 5U;  // 0 to 7
  const std::size_t boards = 1 + (data[3] & 7U);

  std::vector<Single> in;
  std::int64_t t = 0;
  for (std::size_t i = 4; i + 4 <= size; i += 4) {
    t += static_cast<std::int64_t>(data[i]) * 50;  // up to 12.75 ns per step; 0 gives ties
    const std::uint32_t transaxial = (static_cast<std::uint32_t>(data[i + 1]) * 3U) % ScannerGeometry::crystals_per_ring;
    const std::uint32_t ring = data[i + 3] % ScannerGeometry::crystal_rings;
    in.push_back(Single{Picoseconds{t}, ScannerGeometry::make_crystal(ring, transaxial),
                        KeV{300.0F + 2.0F * static_cast<float>(data[i + 2])}});
  }

  // 1. Splitting does not matter.
  SorterStats whole_st;
  SorterStats split_st;
  const auto whole = sort_in_two(c, in, 0, whole_st);
  const auto split = sort_in_two(c, in, in.size() * data[2] / 256, split_st);
  check(whole == split);
  check(whole_st == split_st);

  // 2. Accounting.
  const SorterStats& st = whole_st;
  check(st.singles_in == in.size());
  check(st.prompts + st.delayed == whole.size());
  if (c.mode == WindowMode::fixed) {
    check(st.singles_in ==
          st.energy_rejected + st.out_of_order + st.singles_alone + 2 * st.pair_windows + st.singles_in_multiples);
  }

  // 3. Every pair obeys the rules.
  const CoincidenceSorter judge{c};
  for (const Coincidence& x : whole) {
    const Picoseconds dt = x.time_difference();
    if (x.kind == CoincidenceKind::prompt) {
      check(dt >= Picoseconds{0} && dt <= c.window);
    } else {
      check(c.delay > Picoseconds{0} && dt >= c.delay && dt <= c.delay + c.window);
    }
    check(judge.good(x.first, x.second));
  }

  // 4. The merger gives the stream back from `boards` pieces.
  std::vector<std::vector<Single>> per_board(boards);
  for (std::size_t i = 0; i < in.size(); ++i) {
    per_board[i % boards].push_back(in[i]);
  }
  StreamMerger m{{.boards = boards, .max_skew = Picoseconds{0}}};
  std::vector<Single> merged;
  std::vector<std::size_t> pos(boards, 0);
  std::size_t step = 0;
  for (bool more = true; more;) {
    more = false;
    for (std::size_t b = 0; b < boards; ++b) {
      const std::size_t n = std::min<std::size_t>(per_board[b].size() - pos[b], 1 + (step + b) % 5);
      m.push(b, std::span{per_board[b]}.subspan(pos[b], n));
      pos[b] += n;
      more = more || pos[b] < per_board[b].size();
    }
    ++step;
    m.drain(merged);
  }
  m.flush(merged);
  check(m.stats().late == 0 && m.stats().out_of_order == 0);
  check(merged.size() == in.size());
  for (std::size_t i = 0; i < in.size(); ++i) {
    check(merged[i].time == in[i].time);
  }
  return 0;
}
