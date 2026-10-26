// SPDX-License-Identifier: MIT
// Property-based tests (Chapter 18): statements that must hold for every input
// of a kind, checked on generated inputs that shrink to a small counterexample
// when one fails (tests/support/property.hpp). The example-based tests in the
// other files show the rules on hand-made inputs; these search for the inputs
// nobody thought of.
#include <gtest/gtest-spi.h>
#include <gtest/gtest.h>

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/format/packed_single.hpp"
#include "minidaq/format/readout_packet.hpp"
#include "minidaq/processing/coincidence_sorter.hpp"
#include "minidaq/processing/stream_merger.hpp"
#include "support/property.hpp"

using namespace minidaq;
using G = ScannerGeometry;
using prop::Source;
using prop::Verdict;

namespace {

std::string show(const Single& s) {
  std::ostringstream o;
  o << "{" << s.time.count() << " ps, c" << s.crystal.value() << ", " << s.energy.count() << " keV}";
  return o.str();
}

std::string show(const std::vector<Single>& v) {
  std::ostringstream o;
  o << v.size() << " singles: ";
  for (const auto& s : v) {
    o << show(s) << " ";
  }
  return o.str();
}

// ---------------------------------------------------------------------------
// The time unwrapper

// Absolute times in 5 ps steps: mostly forward, sometimes a little late
// (jitter between channels), with gaps up to just under half a wrap period.
std::vector<std::int64_t> wrapping_times(Source& src) {
  constexpr std::int64_t half = packed::wrap_period_ps / 2;
  const auto n = src.draw(1, 300);
  std::vector<std::int64_t> t;
  std::int64_t newest = src.draw_signed(0, 3 * packed::wrap_period_ps) / packed::time_lsb_ps * packed::time_lsb_ps;
  t.push_back(newest);
  for (std::uint64_t i = 1; i < n; ++i) {
    std::int64_t next = 0;
    switch (src.pick(3)) {
      case 0:  // a small step forward
        next = newest + src.draw_signed(0, 10'000'000);
        break;
      case 1:  // a large gap, up to just under half a wrap
        next = newest + src.draw_signed(0, half - 4 * packed::time_lsb_ps - 1);
        break;
      default:  // a late single, up to 1 us before the newest
        next = std::max<std::int64_t>(0, newest - src.draw_signed(0, 1'000'000));
        break;
    }
    next = next / packed::time_lsb_ps * packed::time_lsb_ps;
    t.push_back(next);
    newest = std::max(newest, next);
  }
  return t;
}

std::string show_times(const std::vector<std::int64_t>& t) {
  std::ostringstream o;
  o << t.size() << " times (ps):";
  for (const auto x : t) {
    o << " " << x;
  }
  return o.str();
}

// [snippet:unwrap_property]
TEST(Properties, TheUnwrapperRestoresEveryTime) {
  // REQ: SRS-FMT-012
  prop::check(wrapping_times,
              [](const std::vector<std::int64_t>& times) -> Verdict {
                packed::TimeUnwrapper u{times.front() / packed::wrap_period_ps};
                for (std::size_t i = 0; i < times.size(); ++i) {
                  const auto code = static_cast<std::uint64_t>(times[i] / packed::time_lsb_ps) & packed::time_mask;
                  if (const auto got = u.unwrap(code).count(); got != times[i]) {
                    return "time " + std::to_string(i) + " came back as " + std::to_string(got);
                  }
                }
                return {};
              },
              show_times);
}
// [/snippet:unwrap_property]

TEST(Properties, PackAndUnpackAreInverse) {
  // REQ: SRS-FMT-010, SRS-FMT-011
  prop::check([](Source& src) {
                return packed::Fields{static_cast<std::uint32_t>(src.draw(0, packed::crystal_mask)),
                                      static_cast<std::uint32_t>(src.draw(0, packed::energy_mask)),
                                      src.draw(0, packed::time_mask)};
              },
              [](const packed::Fields& f) -> Verdict {
                const auto back = packed::unpack(packed::pack(f));
                if (back.crystal != f.crystal || back.energy_code != f.energy_code || back.time_code != f.time_code) {
                  return "a field changed";
                }
                return {};
              },
              [](const packed::Fields& f) {
                return "crystal " + std::to_string(f.crystal) + ", energy " + std::to_string(f.energy_code) +
                       ", time " + std::to_string(f.time_code);
              });
}

// ---------------------------------------------------------------------------
// The coincidence sorter

// A sorter input: a configuration and a stream that is mostly in time order,
// with clusters of singles closer than the window, energies mostly in the
// gate, now and then a single out of order, and every crystal of the scanner
// possible.
struct SorterCase {
  SorterConfig cfg;
  std::vector<Single> singles;
  std::vector<std::size_t> cuts;  // batch boundaries for push()
};

SorterCase sorter_case(Source& src, bool with_delay, std::uint64_t max_singles = 80) {
  SorterCase c;
  c.cfg.window = Picoseconds{src.draw_signed(1, 6'000)};
  c.cfg.delay = with_delay && src.coin(0.7) ? Picoseconds{c.cfg.window.count() * src.draw_signed(2, 30)}
                                            : Picoseconds{0};
  c.cfg.mode = src.coin() ? WindowMode::per_single : WindowMode::fixed;
  c.cfg.multiples = static_cast<MultiplesPolicy>(src.pick(4));
  c.cfg.min_sector_difference = static_cast<std::uint32_t>(src.draw(0, 3));
  c.cfg.fov_radius_mm = src.coin(0.3) ? src.uniform(20.0, 150.0) : 0.0;
  const auto n = src.draw(0, max_singles);
  std::int64_t t = src.draw_signed(0, 1'000'000);
  for (std::uint64_t i = 0; i < n; ++i) {
    const auto step = src.pick(4);
    if (step == 0) {
      // The same time (a tie, common at 5 ps resolution), the same decay or a near random.
      t += src.coin(0.3) ? 0 : src.draw_signed(0, c.cfg.window.count() / 2);
    } else if (step == 1) {
      t += src.draw_signed(0, 2 * c.cfg.window.count());
    } else if (step == 2) {
      t += src.draw_signed(0, 200'000);  // across the delayed window
    } else if (src.coin(0.2)) {
      t -= src.draw_signed(1, 10'000);  // out of order
    }
    const auto crystal = G::make_crystal(static_cast<std::uint32_t>(src.draw(0, G::crystal_rings - 1)),
                                         static_cast<std::uint32_t>(src.draw(0, G::crystals_per_ring - 1)));
    const float kev = src.coin(0.85) ? static_cast<float>(src.uniform(435.0, 585.0001))
                                     : static_cast<float>(src.uniform(0.0, 1000.0));
    c.singles.push_back(Single{Picoseconds{t}, crystal, KeV{kev}});
  }
  for (std::size_t i = 0, k = src.draw(0, 6); i < k && !c.singles.empty(); ++i) {
    c.cuts.push_back(src.draw(0, c.singles.size()));
  }
  std::sort(c.cuts.begin(), c.cuts.end());
  return c;
}

std::string show_case(const SorterCase& c) {
  std::ostringstream o;
  o << "window " << c.cfg.window.count() << " ps, delay " << c.cfg.delay.count() << " ps, "
    << to_string(c.cfg.mode) << ", " << to_string(c.cfg.multiples) << ", sectors " << c.cfg.min_sector_difference
    << ", fov " << c.cfg.fov_radius_mm << " mm, cuts";
  for (const auto x : c.cuts) {
    o << " " << x;
  }
  o << "; " << show(c.singles);
  return o.str();
}

struct Sorted {
  std::vector<Coincidence> out;
  SorterStats stats;
};

Sorted sort_in_batches(const SorterCase& c) {
  CoincidenceSorter s{c.cfg};
  Sorted r;
  std::size_t begin = 0;
  for (const auto cut : c.cuts) {
    s.push(std::span(c.singles).subspan(begin, cut - begin), r.out);
    begin = cut;
  }
  s.push(std::span(c.singles).subspan(begin), r.out);
  s.flush(r.out);
  r.stats = s.stats();
  return r;
}

// A reference sorter written for clarity, not speed: it applies the rules of
// coincidence_sorter.hpp directly to the whole stream. Only the geometry test
// is shared (CoincidenceSorter::good), which has its own tests.
std::vector<Coincidence> reference_prompts(const SorterConfig& cfg, const std::vector<Single>& in) {
  const CoincidenceSorter geometry{cfg};
  std::vector<Single> s;
  for (const auto& x : in) {
    const auto e = static_cast<double>(x.energy.count());
    if (e < cfg.energy_low_kev || e > cfg.energy_high_kev) {
      continue;
    }
    if (!s.empty() && x.time < s.back().time) {
      continue;
    }
    s.push_back(x);
  }
  // Singles with equal times count in crystal order, and two of one crystal in
  // energy order, whatever order they came in.
  std::stable_sort(s.begin(), s.end(), [](const Single& a, const Single& b) {
    if (a.time != b.time) {
      return a.time < b.time;
    }
    return a.crystal != b.crystal ? a.crystal < b.crystal : a.energy.count() < b.energy.count();
  });
  std::vector<Coincidence> out;
  for (std::size_t o = 0; o < s.size();) {
    std::size_t e = o + 1;
    while (e < s.size() && s[e].time - s[o].time <= cfg.window) {
      ++e;
    }
    // The window's candidate pairs: all pairs of the group (fixed), or the
    // opener with each later single (per single).
    std::vector<std::pair<std::size_t, std::size_t>> pairs;
    for (std::size_t i = o; i < (cfg.mode == WindowMode::fixed ? e : o + 1); ++i) {
      for (std::size_t j = i + 1; j < e; ++j) {
        pairs.emplace_back(i, j);
      }
    }
    std::vector<std::pair<std::size_t, std::size_t>> goods;
    for (const auto& [i, j] : pairs) {
      if (geometry.good(s[i], s[j])) {
        goods.emplace_back(i, j);
      }
    }
    if (e - o == 2) {
      for (const auto& [i, j] : goods) {
        out.push_back(Coincidence{s[i], s[j], CoincidenceKind::prompt});
      }
    } else if (e - o > 2) {
      switch (cfg.multiples) {
        case MultiplesPolicy::kill_all:
          break;
        case MultiplesPolicy::take_all_goods:
          for (const auto& [i, j] : goods) {
            out.push_back(Coincidence{s[i], s[j], CoincidenceKind::prompt});
          }
          break;
        case MultiplesPolicy::take_winner_of_goods:
          if (!goods.empty()) {
            // The highest summed energy; on a tie the earlier pair (stable).
            std::stable_sort(goods.begin(), goods.end(), [&](const auto& a, const auto& b) {
              return s[a.first].energy.count() + s[a.second].energy.count() >
                     s[b.first].energy.count() + s[b.second].energy.count();
            });
            out.push_back(Coincidence{s[goods[0].first], s[goods[0].second], CoincidenceKind::prompt});
          }
          break;
        case MultiplesPolicy::keep_if_only_one_good:
          if (goods.size() == 1) {
            out.push_back(Coincidence{s[goods[0].first], s[goods[0].second], CoincidenceKind::prompt});
          }
          break;
      }
    }
    o = cfg.mode == WindowMode::fixed ? e : o + 1;
  }
  return out;
}

std::vector<Coincidence> prompts_of(const std::vector<Coincidence>& v) {
  std::vector<Coincidence> p;
  std::copy_if(v.begin(), v.end(), std::back_inserter(p),
               [](const Coincidence& c) { return c.kind == CoincidenceKind::prompt; });
  return p;
}

// [snippet:sorter_model]
TEST(Properties, TheSorterFindsWhatTheReferenceFinds) {
  // REQ: SRS-SRT-001, SRS-SRT-002, SRS-SRT-003, SRS-SRT-005, SRS-SRT-012
  prop::check([](Source& src) { return sorter_case(src, false); },
              [](const SorterCase& c) -> Verdict {
                const auto got = prompts_of(sort_in_batches(c).out);
                const auto want = reference_prompts(c.cfg, c.singles);
                if (got != want) {
                  return "sorter found " + std::to_string(got.size()) + " prompts, the reference " +
                         std::to_string(want.size());
                }
                return {};
              },
              show_case, {.cases = 500});
}
// [/snippet:sorter_model]

// The pipeline's sort stage orders equal times by crystal within a batch but
// not across batches, so the sorter must not depend on the order of ties
// (found by a system test, MDQ-PR-017).
TEST(Properties, TheOrderOfTiesDoesNotMatter) {
  // REQ: SRS-SRT-013
  prop::check(
      [](Source& src) {
        auto c = sorter_case(src, true);
        auto shuffled = c;
        // Reverse or rotate each run of singles with equal times.
        for (std::size_t i = 0; i < shuffled.singles.size();) {
          std::size_t j = i + 1;
          while (j < shuffled.singles.size() && shuffled.singles[j].time == shuffled.singles[i].time) {
            ++j;
          }
          const auto first = shuffled.singles.begin() + static_cast<std::ptrdiff_t>(i);
          const auto last = shuffled.singles.begin() + static_cast<std::ptrdiff_t>(j);
          if (src.coin()) {
            std::reverse(first, last);
          } else {
            std::rotate(first, first + static_cast<std::ptrdiff_t>(src.draw(0, j - i - 1)), last);
          }
          i = j;
        }
        return std::pair{c, shuffled};
      },
      [](const std::pair<SorterCase, SorterCase>& p) -> Verdict {
        const auto a = sort_in_batches(p.first);
        const auto b = sort_in_batches(p.second);
        if (a.out != b.out || !(a.stats == b.stats)) {
          return "reordering equal times changed the result: " + std::to_string(a.out.size()) + " and " +
                 std::to_string(b.out.size()) + " coincidences";
        }
        return {};
      },
      [](const std::pair<SorterCase, SorterCase>& p) { return show_case(p.first) + " / " + show(p.second.singles); },
      {.cases = 500});
}

// Streams long enough that the sorter compacts its buffer (after 4,096 singles).
TEST(Properties, LongStreamsGiveTheSameResult) {
  // REQ: SRS-SRT-001, SRS-SRT-006, SRS-SRT-008
  prop::check([](Source& src) { return sorter_case(src, false, 12'000); },
              [](const SorterCase& c) -> Verdict {
                if (prompts_of(sort_in_batches(c).out) != reference_prompts(c.cfg, c.singles)) {
                  return "the sorter and the reference differ";
                }
                return {};
              },
              [](const SorterCase& c) { return std::to_string(c.singles.size()) + " singles"; }, {.cases = 20});
}

TEST(Properties, EveryCoincidenceIsInItsWindow) {
  // REQ: SRS-SRT-001, SRS-SRT-006
  prop::check([](Source& src) { return sorter_case(src, true); },
              [](const SorterCase& c) -> Verdict {
                for (const auto& k : sort_in_batches(c).out) {
                  const auto dt = k.time_difference();
                  const auto lo = k.kind == CoincidenceKind::prompt ? Picoseconds{0} : c.cfg.delay;
                  if (dt < lo || dt > lo + c.cfg.window) {
                    return "a " + std::string{k.kind == CoincidenceKind::prompt ? "prompt" : "delayed"} +
                           " coincidence " + std::to_string(dt.count()) + " ps apart";
                  }
                }
                return {};
              },
              show_case);
}

// [snippet:used_once]
// In a fixed window every single belongs to one window, and every policy
// except take_all_goods emits at most one pair per window: no single may then
// be in two prompts.
TEST(Properties, FixedWindowsUseEachSingleOnce) {
  // REQ: SRS-SRT-002, SRS-SRT-003
  prop::check(
      [](Source& src) {
        auto c = sorter_case(src, false);
        c.cfg.mode = WindowMode::fixed;
        if (c.cfg.multiples == MultiplesPolicy::take_all_goods) {
          c.cfg.multiples = MultiplesPolicy::kill_all;
        }
        return c;
      },
      [](const SorterCase& c) -> Verdict {
        std::map<std::tuple<std::int64_t, std::uint32_t, float>, int> uses;
        for (const auto& k : prompts_of(sort_in_batches(c).out)) {
          for (const auto& s : {k.first, k.second}) {
            if (++uses[{s.time.count(), s.crystal.value(), s.energy.count()}] > 1) {
              return "single " + show(s) + " is in two prompts";
            }
          }
        }
        return {};
      },
      show_case);
}
// [/snippet:used_once]

TEST(Properties, BatchSizesDoNotMatter) {
  // REQ: SRS-SRT-008
  prop::check([](Source& src) { return sorter_case(src, true); },
              [](const SorterCase& c) -> Verdict {
                SorterCase whole = c;
                whole.cuts.clear();
                const auto a = sort_in_batches(c);
                const auto b = sort_in_batches(whole);
                if (a.out != b.out) {
                  return "different coincidences";
                }
                if (!(a.stats == b.stats)) {
                  return "different counters";
                }
                return {};
              },
              show_case);
}

TEST(Properties, EverySingleIsAccountedFor) {
  // REQ: SRS-SRT-009
  prop::check(
      [](Source& src) {
        auto c = sorter_case(src, true);
        c.cfg.mode = WindowMode::fixed;  // the identity of coincidence_sorter.hpp is for fixed windows
        return c;
      },
      [](const SorterCase& c) -> Verdict {
        const auto st = sort_in_batches(c).stats;
        const auto sum = st.energy_rejected + st.out_of_order + st.singles_alone + (2 * st.pair_windows) +
                         st.singles_in_multiples;
        if (st.singles_in != c.singles.size() || sum != st.singles_in) {
          return std::to_string(st.singles_in) + " singles in, " + std::to_string(sum) + " accounted for";
        }
        return {};
      },
      show_case);
}

// ---------------------------------------------------------------------------
// The sequence tracker

// A link: packets from a starting sequence number near the wrap of the
// counter, each displaced by fewer places than the reorder window, some lost
// (in half of the cases) and a few duplicated. The first packet is never lost
// or displaced: it defines where the stream starts. Fewer duplicates than the
// window, so no run of stale packets looks like a restart of the source.
struct LinkCase {
  std::uint32_t first = 0;
  std::size_t packets = 0;
  std::vector<std::uint32_t> arrivals;  // sequence numbers in arrival order
  std::size_t window = 8;
  bool lossy = false;
};

LinkCase link_case(Source& src) {
  LinkCase c;
  c.first = static_cast<std::uint32_t>(0xFFFF'FFFFU - src.draw(0, 100));  // across the wrap
  c.packets = src.draw(1, 200);
  c.window = std::size_t{1} << src.draw(1, 5);
  c.lossy = src.coin();
  std::size_t duplicates = 0;
  std::vector<std::pair<std::uint64_t, std::uint32_t>> keyed;  // (arrival position, sequence)
  keyed.emplace_back(0, c.first);
  for (std::size_t i = 1; i < c.packets; ++i) {
    const auto seq = static_cast<std::uint32_t>(c.first + i);
    if (c.lossy && src.coin(0.1)) {
      continue;
    }
    keyed.emplace_back((4 * i) + src.draw(0, 4 * (c.window - 1)), seq);
    if (duplicates + 1 < c.window && src.coin(0.05)) {
      ++duplicates;
      keyed.emplace_back((4 * i) + src.draw(0, 4 * (c.window - 1)), seq);
    }
  }
  std::stable_sort(keyed.begin(), keyed.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
  for (const auto& k : keyed) {
    c.arrivals.push_back(k.second);
  }
  return c;
}

std::string show_link(const LinkCase& c) {
  std::ostringstream o;
  o << "first " << c.first << ", " << c.packets << " packets, window " << c.window << ", arrivals:";
  for (const auto s : c.arrivals) {
    o << " " << static_cast<std::uint32_t>(s - c.first);
  }
  return o.str();
}

// [snippet:tracker_property]
TEST(Properties, TheTrackerRestoresOrderAndCountsEveryPacket) {
  // REQ: SRS-RDO-003, SRS-RDO-004, SRS-RDO-007
  prop::check(link_case,
              [](const LinkCase& c) -> Verdict {
                using namespace readout;
                SequenceTracker tracker{{.window_packets = c.window, .max_hold_ns = 1'000'000'000}};
                std::vector<std::uint32_t> delivered;
                const auto deliver = [&](const PacketHeader& h, std::span<const std::byte>) {
                  delivered.push_back(h.sequence);
                };
                std::array<std::byte, max_packet_bytes> buf{};
                const std::array<std::uint64_t, 1> word{42};
                std::int64_t now = 0;
                for (const auto seq : c.arrivals) {
                  const std::size_t len = encode_packet({.sequence = seq, .word_count = 1}, word, buf);
                  const auto p = parse_packet(std::span(buf).first(len));
                  if (!p) {
                    return "a packet did not parse";
                  }
                  tracker.offer(*p, now += 1'000, deliver);
                }
                tracker.flush(deliver);
                const auto& st = tracker.stats();
                for (std::size_t i = 1; i < delivered.size(); ++i) {
                  if (sequence_distance(delivered[i - 1], delivered[i]) <= 0) {
                    return "delivery out of order at " + std::to_string(i);
                  }
                }
                if (st.received != c.arrivals.size() || st.received != st.delivered + st.stale) {
                  return "received " + std::to_string(st.received) + " != delivered + stale";
                }
                if (st.resyncs != 0) {
                  return "a resynchronization";
                }
                // Every number from the first to the last delivered is delivered or declared lost.
                const auto span = static_cast<std::uint64_t>(sequence_distance(delivered.front(), delivered.back())) + 1;
                if (st.delivered + st.lost != span) {
                  return "delivered + lost = " + std::to_string(st.delivered + st.lost) + ", span " +
                         std::to_string(span);
                }
                // Without loss, the window is enough to deliver every packet once.
                if (!c.lossy && (st.delivered != c.packets || st.lost != 0)) {
                  return std::to_string(st.delivered) + " delivered, " + std::to_string(st.lost) + " lost";
                }
                // Every packet that arrives is delivered once, unless it is a duplicate.
                const std::set<std::uint32_t> arrived(c.arrivals.begin(), c.arrivals.end());
                if (st.delivered != arrived.size()) {
                  return std::to_string(arrived.size()) + " arrived, " + std::to_string(st.delivered) + " delivered";
                }
                return {};
              },
              show_link);
}
// [/snippet:tracker_property]

// ---------------------------------------------------------------------------
// The stream merger

struct MergeCase {
  std::size_t boards = 1;
  std::vector<std::vector<Single>> streams;          // each in time order
  std::vector<std::pair<std::size_t, std::size_t>> plan;  // (board, how many singles to push next)
  std::vector<bool> drain_after;                     // drain after each push
};

MergeCase merge_case(Source& src) {
  MergeCase c;
  c.boards = src.draw(1, 5);
  c.streams.resize(c.boards);
  for (std::size_t b = 0; b < c.boards; ++b) {
    std::int64_t t = src.draw_signed(0, 5'000);
    for (std::size_t i = 0, n = src.draw(0, 40); i < n; ++i) {
      t += src.draw_signed(0, 3'000);  // equal times happen
      c.streams[b].push_back(Single{Picoseconds{t}, CrystalId{static_cast<std::uint32_t>(b)}, KeV{511.0F}});
    }
  }
  std::vector<std::size_t> left(c.boards);
  for (std::size_t b = 0; b < c.boards; ++b) {
    left[b] = c.streams[b].size();
  }
  for (std::size_t b = 0; b < c.boards; ++b) {
    while (left[b] > 0) {
      const auto board = src.pick(c.boards);
      const auto k = std::min<std::size_t>(left[board], src.draw(0, 8));
      c.plan.emplace_back(board, k);
      c.drain_after.push_back(src.coin(0.3));
      left[board] -= k;
    }
  }
  return c;
}

std::string show_merge(const MergeCase& c) {
  std::ostringstream o;
  o << c.boards << " boards;";
  for (std::size_t b = 0; b < c.boards; ++b) {
    o << " board " << b << ":";
    for (const auto& s : c.streams[b]) {
      o << " " << s.time.count();
    }
    o << ";";
  }
  o << " pushes:";
  for (std::size_t i = 0; i < c.plan.size(); ++i) {
    o << " " << c.plan[i].first << "x" << c.plan[i].second << (c.drain_after[i] ? "d" : "");
  }
  return o.str();
}

TEST(Properties, TheMergerOutputIsOrderedAndComplete) {
  // REQ: SRS-MRG-001, SRS-MRG-002
  prop::check(merge_case,
              [](const MergeCase& c) -> Verdict {
                StreamMerger m{{.boards = c.boards, .max_skew = Picoseconds{0}}};  // wait for every board
                std::vector<std::size_t> next(c.boards, 0);
                std::vector<Single> out;
                for (std::size_t i = 0; i < c.plan.size(); ++i) {
                  const auto [board, k] = c.plan[i];
                  m.push(board, std::span(c.streams[board]).subspan(next[board], k));
                  next[board] += k;
                  if (c.drain_after[i]) {
                    m.drain(out);
                  }
                }
                m.flush(out);
                if (!std::is_sorted(out.begin(), out.end(),
                                    [](const Single& a, const Single& b) { return a.time < b.time; })) {
                  return "output not in time order";
                }
                std::vector<Single> all;
                for (const auto& s : c.streams) {
                  all.insert(all.end(), s.begin(), s.end());
                }
                const auto key = [](const Single& a, const Single& b) {
                  return std::tuple{a.time.count(), a.crystal.value()} < std::tuple{b.time.count(), b.crystal.value()};
                };
                std::sort(all.begin(), all.end(), key);
                auto got = out;
                std::sort(got.begin(), got.end(), key);
                if (got != all || m.stats().late != 0) {
                  return std::to_string(out.size()) + " out of " + std::to_string(all.size()) + ", " +
                         std::to_string(m.stats().late) + " late";
                }
                return {};
              },
              show_merge);
}

// ---------------------------------------------------------------------------
// The harness itself: a property that is false must fail, and shrink.

TEST(Properties, TheHarnessShrinksACounterexample) {
  // "No list of numbers sums to more than 1000" is false. Shrinking finds a
  // counterexample that is locally minimal: lowering any one number, or
  // removing one, makes the property hold, so the sum is exactly 1001.
  ::testing::TestPartResultArray failures;
  {
    ::testing::ScopedFakeTestPartResultReporter reporter{
        ::testing::ScopedFakeTestPartResultReporter::INTERCEPT_ONLY_CURRENT_THREAD, &failures};
    prop::check(
        [](Source& src) {
          std::vector<std::uint64_t> v(src.draw(0, 50));
          for (auto& x : v) {
            x = src.draw(0, 1000);
          }
          return v;
        },
        [](const std::vector<std::uint64_t>& v) -> Verdict {
          std::uint64_t sum = 0;
          for (const auto x : v) {
            sum += x;
          }
          return sum > 1000 ? "sum " + std::to_string(sum) : "";
        },
        [](const std::vector<std::uint64_t>& v) {
          std::string s = std::to_string(v.size()) + " numbers:";
          for (const auto x : v) {
            s += " " + std::to_string(x);
          }
          return s;
        });
  }
  ASSERT_EQ(failures.size(), 1);
  const std::string msg = failures.GetTestPartResult(0).message();
  EXPECT_NE(msg.find("property failed: sum 1001\n"), std::string::npos) << msg;
  EXPECT_NE(msg.find("replay: MINIDAQ_PROP_REPLAY="), std::string::npos) << msg;
}

}  // namespace
