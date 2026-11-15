// SPDX-License-Identifier: MIT
// Time markers of the readout (Chapter 24, CR-0026, MDQ-PR-007): the marker word of MDQ-P1
// revision 1.1, the decoder that reads it, the coincidence sorter that closes its windows on it,
// and the simulated board that sends it.
#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <cstdint>
#include <limits>
#include <optional>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/format/packed_single.hpp"
#include "minidaq/processing/coincidence_sorter.hpp"
#include "minidaq/sim/detector_simulator.hpp"
#include "minidaq/sim/readout_link.hpp"

using namespace minidaq;
using G = ScannerGeometry;
namespace p = minidaq::packed;

namespace {

Single at(std::int64_t t_ps, std::uint32_t transaxial, float kev = 511.0F) {
  return Single{Picoseconds{t_ps}, G::make_crystal(0, transaxial), KeV{kev}};
}

SorterConfig plain() {
  SorterConfig c;
  c.delay = Picoseconds{0};
  c.min_sector_difference = 0;
  return c;
}

std::vector<sim::TruthSingle> simulate(double activity_bq, double seconds, std::uint64_t seed) {
  sim::SimulatorConfig c;
  c.activity_bq = activity_bq;
  c.source = {sim::SourceShape::Kind::cylinder, {0.0, 0.0, 0.0}, 80.0, 100.0};
  c.phantom = {90.0, 180.0};
  c.seed = seed;
  sim::DetectorSimulator d{c};
  return d.generate_until(Picoseconds{static_cast<std::int64_t>(seconds * 1e12)});
}

}  // namespace

TEST(TimeMarker, IsAWordThatNoSingleOfTheScannerCanBe) {
  // REQ: SRS-FMT-014
  const std::uint64_t m = p::marker(123'456);
  EXPECT_TRUE(p::is_marker(m));
  EXPECT_EQ(p::unpack(m).time_code, 123'456U);
  EXPECT_EQ(p::unpack(m).crystal, 32'767U);
  EXPECT_EQ(p::unpack(m).energy_code, 2'047U);
  // The largest crystal of the scanner, at the saturated energy, is still a single.
  EXPECT_FALSE(p::is_marker(
      p::encode(Single{Picoseconds{5}, CrystalId{G::num_crystals - 1}, KeV{5000.0F}})));
  // Crystal 32767 at another energy is not a marker: an invalid single, as before.
  EXPECT_FALSE(p::is_marker(p::pack({p::marker_crystal, 100, 7})));
  EXPECT_GT(p::marker_crystal, G::num_crystals - 1);
}

TEST(StreamDecoder, ReadsAMarkerAsAPromiseNotASingle) {
  // REQ: SRS-FMT-014
  // REQ: SRS-FMT-013
  const std::vector<std::uint64_t> words = {
      p::encode(Single{Picoseconds{1'000}, CrystalId{10}, KeV{511.0F}}),
      p::marker(400),                        // 2 ns
      p::pack({G::num_crystals, 100, 500}),  // an invalid single: still counted as such
      p::marker(300),                        // an earlier marker does not move the promise back
      p::encode(Single{Picoseconds{3'000}, CrystalId{20}, KeV{300.0F}}),
  };
  std::array<Single, 8> out{};
  p::StreamDecoder d{G::num_crystals};
  ASSERT_EQ(d.decode(words, out), 2U);
  EXPECT_EQ(out[0].crystal, CrystalId{10});
  EXPECT_EQ(out[1].crystal, CrystalId{20});
  EXPECT_EQ(d.stats().words, 5U);
  EXPECT_EQ(d.stats().markers, 2U);
  EXPECT_EQ(d.stats().invalid_crystal, 1U);
  const std::optional<Picoseconds> m = d.take_marker();
  ASSERT_TRUE(m.has_value());
  EXPECT_EQ(m->count(), 2'000);
  EXPECT_FALSE(d.take_marker().has_value()) << "taken once";
}

TEST(StreamDecoder, UnwrapsAMarkerLikeASingle) {
  // REQ: SRS-FMT-014
  const std::uint64_t near_end = p::time_mask - 10;
  const std::vector<std::uint64_t> words = {
      p::encode(
          Single{Picoseconds{static_cast<std::int64_t>(near_end) * 5}, CrystalId{1}, KeV{511.0F}}),
      p::marker(4)};  // after the counter wrapped
  std::array<Single, 4> out{};
  p::StreamDecoder d{G::num_crystals};
  ASSERT_EQ(d.decode(words, out), 1U);
  EXPECT_EQ(d.take_marker()->count(), p::wrap_period_ps + 20);
}

TEST(CoincidenceSorter, AMarkerClosesTheWindowsBeforeIt) {
  // REQ: SRS-SRT-014
  const SorterConfig c = plain();
  CoincidenceSorter s{c};
  std::vector<Coincidence> out;
  const std::vector<Single> pair = {at(1'000'000, 0), at(1'001'000, 192)};
  s.push(pair, out);
  EXPECT_TRUE(out.empty()) << "without later data the window stays open (MDQ-PR-007)";
  EXPECT_EQ(s.held(), 2U);

  s.advance(Picoseconds{1'000'000 + c.window.count()}, out);  // a single here could still join
  EXPECT_TRUE(out.empty());
  s.advance(Picoseconds{1'000'000 + c.window.count() + 1}, out);
  ASSERT_EQ(out.size(), 1U);
  EXPECT_EQ(out[0].first, pair[0]);
  EXPECT_EQ(out[0].second, pair[1]);
  EXPECT_EQ(s.stats().prompts, 1U);

  // The marker is a promise: a single before it is out of order, one at it is not.
  const Picoseconds promised{1'000'000 + c.window.count() + 1};
  const std::vector<Single> late = {at(promised.count() - 1, 5), at(promised.count(), 6)};
  s.push(late, out);
  EXPECT_EQ(s.stats().out_of_order, 1U);
  // A marker earlier than what was seen changes nothing.
  s.advance(Picoseconds{0}, out);
  s.flush(out);
  EXPECT_EQ(s.stats().singles_in, 4U);
  EXPECT_EQ(s.stats().singles_alone, 1U);
  EXPECT_EQ(out.size(), 1U);
}

TEST(CoincidenceSorter, MarkersChangeNoCoincidence) {
  // REQ: SRS-SRT-014
  // REQ: SRS-SRT-008
  // Markers between the singles, each at the earliest time still to come (the promise a board
  // keeps), in both window modes and with the delayed window: the same coincidences and counters
  // as without markers.
  const auto truth = simulate(4e6, 0.002, 41);
  std::vector<Single> singles;
  for (const auto& t : truth) {
    singles.push_back(t.single);
  }
  ASSERT_GT(singles.size(), 2'000U);
  std::vector<std::int64_t> earliest_after(singles.size() + 1,
                                           std::numeric_limits<std::int64_t>::max());
  for (std::size_t i = singles.size(); i-- > 0;) {
    earliest_after[i] = std::min(earliest_after[i + 1], singles[i].time.count());
  }
  for (const WindowMode mode : {WindowMode::fixed, WindowMode::per_single}) {
    SorterConfig c;
    c.mode = mode;
    c.multiples = MultiplesPolicy::take_all_goods;
    CoincidenceSorter plain_sorter{c};
    std::vector<Coincidence> want;
    plain_sorter.push(singles, want);
    plain_sorter.flush(want);

    CoincidenceSorter marked{c};
    std::vector<Coincidence> got;
    std::size_t emitted_early = 0;
    for (std::size_t i = 0; i < singles.size(); i += 37) {
      const std::size_t n = std::min<std::size_t>(37, singles.size() - i);
      marked.push(std::span(singles).subspan(i, n), got);
      if (earliest_after[i + n] != std::numeric_limits<std::int64_t>::max()) {
        marked.advance(Picoseconds{earliest_after[i + n]}, got);
      }
      emitted_early = got.size();
    }
    marked.flush(got);
    EXPECT_EQ(got, want) << to_string(mode);
    EXPECT_EQ(marked.stats(), plain_sorter.stats()) << to_string(mode);
    EXPECT_GT(emitted_early, want.size() / 2) << "the markers did close windows before the flush";
  }
}

TEST(ReadoutLink, SendsAMarkerAtEveryIntervalBeforeTheDataAfterIt) {
  // REQ: SRS-FMT-014
  const auto truth = simulate(1e6, 0.001, 3);  // 1 ms
  const Picoseconds interval{100'000'000};     // 100 us
  const Picoseconds end{1'000'000'000};
  const auto words = sim::encode_with_markers(truth, interval, end);
  ASSERT_EQ(words.size(), truth.size() + 10) << "a marker at 100, 200, ... 1000 us";

  std::vector<Single> singles(words.size());
  p::StreamDecoder d{G::num_crystals};
  std::int64_t promised = std::numeric_limits<std::int64_t>::min();
  std::size_t k = 0;
  for (const std::uint64_t w : words) {
    std::array<Single, 1> one{};
    if (d.decode(std::span(&w, 1), one) == 1) {
      EXPECT_GE(one[0].time.count(), promised) << "no single before a marker already sent";
      singles[k++] = one[0];
    } else {
      const auto m = d.take_marker();
      ASSERT_TRUE(m.has_value());
      EXPECT_EQ(m->count() % interval.count(), 0);
      promised = m->count();
    }
  }
  EXPECT_EQ(k, truth.size());
  EXPECT_EQ(d.stats().markers, 10U);
  EXPECT_EQ(promised, end.count());
  EXPECT_EQ(sim::encode_with_markers(truth, Picoseconds{0}, end).size(), truth.size())
      << "0: no markers";
}
