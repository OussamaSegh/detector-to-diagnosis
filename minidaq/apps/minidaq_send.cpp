// SPDX-License-Identifier: MIT
// minidaq_send: play the part of a readout link (Chapter 9). Simulates singles
// with the detector simulator, cuts them into MDQ-R1 packets, optionally
// damages the packet stream, and sends it over UDP, paced like the detector
// would produce it or as fast as possible.
//
//   minidaq_send --port 7701 --activity 2e6 --seconds 1 --loss 0.001 --reorder 0.001
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <algorithm>
#include <cerrno>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <string>
#include <string_view>
#include <thread>
#include <vector>

#include "minidaq/core/clock.hpp"
#include "minidaq/core/parse_number.hpp"
#include "minidaq/format/packed_single.hpp"
#include "minidaq/sim/detector_simulator.hpp"
#include "minidaq/sim/readout_link.hpp"

namespace {

constexpr const char* usage =
    "usage: minidaq_send [--host IPV4] [--port N] [--activity BQ] [--seconds S] [--phantom RADIUS_MM]\n"
    "                    [--words-per-packet N] [--first-sequence N] [--source-id N] [--seed N]\n"
    "                    [--loss P] [--reorder P] [--duplicate P] [--speed F]\n"
    "  --speed 1 sends in real time (detector time), 2 twice as fast, 0 as fast as possible\n";

struct Options {
  std::string host = "127.0.0.1";
  std::uint16_t port = 7701;
  double seconds = 0.2;
  double phantom_mm = 90.0;
  double speed = 1.0;
  minidaq::sim::SimulatorConfig sim;
  minidaq::sim::PacketizerConfig packets;
  minidaq::sim::LinkFaultConfig faults;
};

bool parse(int argc, char** argv, Options& o) {
  for (int i = 1; i < argc; i += 2) {  // every option takes a value
    const std::string_view a{argv[i]};
    const std::string_view v = i + 1 < argc ? argv[i + 1] : "";
    std::uint64_t n = 0;
    bool ok = true;
    if (a == "--host" && !v.empty()) {
      o.host = v;
    } else if (a == "--port") {
      ok = minidaq::parse_into(v, n, std::uint64_t{1}, std::uint64_t{65535});
      o.port = static_cast<std::uint16_t>(n);
    } else if (a == "--activity") {
      ok = minidaq::parse_into(v, o.sim.activity_bq, 1.0, 1e10);
    } else if (a == "--seconds") {
      ok = minidaq::parse_into(v, o.seconds, 1e-6, 10.0);  // all packets are prepared in memory
    } else if (a == "--phantom") {
      ok = minidaq::parse_into(v, o.phantom_mm, 0.0, 140.0);
    } else if (a == "--words-per-packet") {
      ok = minidaq::parse_into(v, o.packets.words_per_packet, std::size_t{1}, minidaq::readout::max_words);
    } else if (a == "--first-sequence") {
      ok = minidaq::parse_into(v, n, std::uint64_t{0}, std::uint64_t{0xFFFFFFFF});
      o.packets.first_sequence = static_cast<std::uint32_t>(n);
    } else if (a == "--source-id") {
      ok = minidaq::parse_into(v, n, std::uint64_t{0}, std::uint64_t{65535});
      o.packets.source = static_cast<std::uint16_t>(n);
    } else if (a == "--seed") {
      ok = minidaq::parse_into(v, o.sim.seed, std::uint64_t{0}, ~std::uint64_t{0});
      o.faults.seed = o.sim.seed + 1;
    } else if (a == "--loss") {
      ok = minidaq::parse_into(v, o.faults.loss, 0.0, 1.0);
    } else if (a == "--reorder") {
      ok = minidaq::parse_into(v, o.faults.reorder, 0.0, 1.0);
    } else if (a == "--duplicate") {
      ok = minidaq::parse_into(v, o.faults.duplicate, 0.0, 1.0);
    } else if (a == "--speed") {
      ok = minidaq::parse_into(v, o.speed, 0.0, 1000.0);
    } else {
      ok = false;
    }
    if (!ok) {
      return false;
    }
  }
  return true;
}

// Detector time of the first single in a packet, from its first word.
std::int64_t packet_time_ps(const minidaq::sim::Datagram& d, minidaq::packed::TimeUnwrapper& unwrap) {
  const auto p = minidaq::readout::parse_packet(d.bytes);
  const auto f = minidaq::packed::unpack(minidaq::readout::payload_word(p->payload, 0));
  return unwrap.unwrap(f.time_code).count();
}

}  // namespace

int main(int argc, char** argv) {
  using namespace minidaq;
  Options o;
  if (!parse(argc, argv, o)) {
    std::fputs(usage, stderr);
    return 2;
  }
  if (o.phantom_mm > 0.0) {
    o.sim.source = {sim::SourceShape::Kind::cylinder, {0.0, 0.0, 0.0}, std::min(80.0, o.phantom_mm - 10.0), 100.0};
    o.sim.phantom = {o.phantom_mm, 180.0};
  }
  if (auto v = sim::validate(o.sim); !v) {
    std::fprintf(stderr, "minidaq_send: %s\n", v.error().c_str());
    return 2;
  }
  sockaddr_in to{};
  to.sin_family = AF_INET;
  to.sin_port = htons(o.port);
  if (inet_pton(AF_INET, o.host.c_str(), &to.sin_addr) != 1) {
    std::fprintf(stderr, "minidaq_send: \"%s\" is not an IPv4 address\n", o.host.c_str());
    return 2;
  }

  // 1. Detector: singles in time order, encoded as MDQ-P1 words.
  sim::DetectorSimulator detector{o.sim};
  const auto singles = detector.generate_until(Picoseconds{static_cast<std::int64_t>(o.seconds * 1e12)});
  std::vector<std::uint64_t> words;
  words.reserve(singles.size());
  for (const auto& s : singles) {
    words.push_back(packed::encode(s.single));
  }
  // 2. Readout link: packets, then the network's damage.
  sim::Packetizer packetizer{o.packets};
  auto packets = packetizer.packetize(words, /*end=*/true);
  const std::size_t prepared = packets.size();
  sim::LinkFaults faults{o.faults};
  faults.apply(packets);

  // 3. Send, paced by detector time: a packet leaves once its first single
  // has "happened", scaled by --speed.
  const int fd = ::socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
  if (fd < 0) {
    std::fprintf(stderr, "minidaq_send: socket: %s\n", std::strerror(errno));  // NOLINT(concurrency-mt-unsafe)
    return 1;
  }
  packed::TimeUnwrapper unwrap;
  const std::int64_t t0_ns = monotonic_ns();
  std::size_t sent = 0;
  std::uint64_t bytes = 0;
  std::uint64_t send_errors = 0;
  for (const auto& d : packets) {
    if (o.speed > 0.0) {
      const auto due_ns = t0_ns + static_cast<std::int64_t>(static_cast<double>(packet_time_ps(d, unwrap)) / 1000.0 / o.speed);
      while (monotonic_ns() < due_ns) {
        std::this_thread::sleep_for(std::chrono::microseconds(20));
      }
    }
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast): sockets API
    const auto n = ::sendto(fd, d.bytes.data(), d.bytes.size(), 0, reinterpret_cast<const sockaddr*>(&to), sizeof to);
    if (n == static_cast<ssize_t>(d.bytes.size())) {
      ++sent;
      bytes += d.bytes.size();
    } else {
      ++send_errors;
    }
  }
  const double elapsed = static_cast<double>(monotonic_ns() - t0_ns) * 1e-9;
  ::close(fd);

  const auto& f = faults.counts();
  std::printf("singles %zu in %.3g s of detector time (%.3g Bq)\n", singles.size(), o.seconds, o.sim.activity_bq);
  std::printf("packets %zu of up to %zu words, sequence %u .. %u\n", prepared, o.packets.words_per_packet,
              o.packets.first_sequence, packetizer.next_sequence() - 1U);
  std::printf("injected: lost %llu, delayed %llu, duplicated %llu\n", static_cast<unsigned long long>(f.lost),
              static_cast<unsigned long long>(f.delayed), static_cast<unsigned long long>(f.duplicated));
  std::printf("sent %zu datagrams, %.3g MB in %.3f s: %.0f packets/s, %.1f Mbit/s, %llu send errors\n", sent,
              static_cast<double>(bytes) * 1e-6, elapsed, static_cast<double>(sent) / elapsed,
              static_cast<double>(bytes) * 8e-6 / elapsed, static_cast<unsigned long long>(send_errors));
  return send_errors == 0 ? 0 : 1;
}
