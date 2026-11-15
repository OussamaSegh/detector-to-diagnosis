// SPDX-License-Identifier: MIT
#include "minidaq/sim/readout_link.hpp"

#include "minidaq/core/geometry.hpp"
#include "minidaq/format/packed_single.hpp"

#include <algorithm>
#include <array>
#include <stdexcept>
#include <utility>

namespace minidaq::sim {

Packetizer::Packetizer(PacketizerConfig cfg) : cfg_{cfg}, next_{cfg.first_sequence} {
  if (cfg_.words_per_packet < 1 || cfg_.words_per_packet > readout::max_words) {
    throw std::invalid_argument("Packetizer: words_per_packet must be in [1, 1024]");
  }
}

std::vector<Datagram> Packetizer::packetize(std::span<const std::uint64_t> words, bool end) {
  std::vector<Datagram> out;
  out.reserve((words.size() + cfg_.words_per_packet - 1) / cfg_.words_per_packet);
  for (std::size_t at = 0; at < words.size(); at += cfg_.words_per_packet) {
    const auto chunk = words.subspan(at, std::min(cfg_.words_per_packet, words.size() - at));
    readout::PacketHeader h;
    h.source = cfg_.source;
    h.sequence = next_++;  // unsigned: wraps from 2^32 - 1 to 0 by definition
    h.word_count = static_cast<std::uint16_t>(chunk.size());
    if (end && at + chunk.size() == words.size()) {
      h.flags = readout::flag_end_of_stream;
    }
    Datagram d{h.sequence, std::vector<std::byte>(readout::header_bytes + chunk.size() * readout::word_bytes)};
    (void)readout::encode_packet(h, chunk, d.bytes);
    out.push_back(std::move(d));
  }
  return out;
}

std::vector<std::uint64_t> encode_with_markers(std::span<const TruthSingle> singles,
                                               Picoseconds interval, Picoseconds end) {
  std::vector<std::uint64_t> words;
  const std::int64_t step = interval.count();
  const std::size_t markers =
      step > 0 && end.count() > 0 ? static_cast<std::size_t>(end.count() / step) : 0;
  words.reserve(singles.size() + markers);
  const auto marker_at = [](std::int64_t t_ps) {
    return packed::marker(static_cast<std::uint64_t>(t_ps / packed::time_lsb_ps) &
                          packed::time_mask);
  };
  std::int64_t next = step;  // the first marker; none at time 0, before any data
  for (const TruthSingle& s : singles) {
    while (step > 0 && next <= s.single.time.count() && next <= end.count()) {
      words.push_back(marker_at(next));
      next += step;
    }
    words.push_back(packed::encode(s.single));
  }
  while (step > 0 && next <= end.count()) {
    words.push_back(marker_at(next));
    next += step;
  }
  return words;
}

LinkFaults::LinkFaults(LinkFaultConfig cfg) : cfg_{cfg}, rng_{cfg.seed} {
  const auto probability = [](double p) { return p >= 0.0 && p <= 1.0; };
  if (!probability(cfg_.loss) || !probability(cfg_.reorder) || !probability(cfg_.duplicate) ||
      cfg_.max_displacement < 1) {
    throw std::invalid_argument("LinkFaults: probabilities must be in [0, 1], max_displacement >= 1");
  }
}

// [snippet:apply]
void LinkFaults::apply(std::vector<Datagram>& packets) {
  std::vector<Datagram> out;
  out.reserve(packets.size() + packets.size() / 8);
  struct Delayed {
    std::size_t release_after;  // position in `out` after which it is sent
    Datagram packet;
  };
  std::vector<Delayed> delayed;
  std::uniform_int_distribution<std::size_t> shift{1, cfg_.max_displacement};
  auto release = [&] {
    // Send every delayed packet whose turn has come, oldest first.
    for (auto it = delayed.begin(); it != delayed.end();) {
      if (it->release_after < out.size()) {
        out.push_back(std::move(it->packet));
        it = delayed.erase(it);
      } else {
        ++it;
      }
    }
  };
  for (auto& p : packets) {
    ++counts_.offered;
    if (unit_(rng_) < cfg_.loss) {
      ++counts_.lost;
      continue;
    }
    const bool dup = unit_(rng_) < cfg_.duplicate;
    if (unit_(rng_) < cfg_.reorder) {
      ++counts_.delayed;
      if (dup) {
        ++counts_.duplicated;
        ++counts_.delayed_duplicated;
        out.push_back(p);  // the copy goes on time, the original late
      }
      delayed.push_back({out.size() + shift(rng_) - 1, std::move(p)});
    } else {
      if (dup) {
        ++counts_.duplicated;
        out.push_back(p);
      }
      out.push_back(std::move(p));
    }
    release();
  }
  for (auto& d : delayed) {
    out.push_back(std::move(d.packet));  // end of stream: whatever is still waiting
  }
  packets = std::move(out);
}
// [/snippet:apply]

void quantize_as_on_link(std::span<TruthSingle> singles) {
  packed::StreamDecoder decoder{ScannerGeometry::num_crystals};
  for (auto& s : singles) {
    const std::array<std::uint64_t, 1> word{packed::encode(s.single)};
    std::array<Single, 1> out{};
    if (decoder.decode(word, out) != 1) {
      throw std::invalid_argument("quantize_as_on_link: a single's crystal is not in the scanner");
    }
    s.single = out[0];
  }
}

}  // namespace minidaq::sim
