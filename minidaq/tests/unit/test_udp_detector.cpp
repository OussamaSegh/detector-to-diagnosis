// SPDX-License-Identifier: MIT
// The UDP readout adapter over the loopback interface: real sockets, injected
// faults, every packet accounted for.
#include <gtest/gtest.h>

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <map>
#include <numeric>
#include <span>
#include <thread>
#include <vector>

#include <nlohmann/json.hpp>

#include "minidaq/control/acquisition_service.hpp"
#include "minidaq/control/adapters.hpp"
#include "minidaq/control/udp_detector.hpp"
#include "minidaq/format/packed_single.hpp"
#include "minidaq/sim/readout_link.hpp"
#include "traced.hpp"

using namespace minidaq;
using namespace minidaq::control;

namespace {

// A sending socket for the tests, closed on destruction.
class Sender {
 public:
  explicit Sender(std::uint16_t port) : fd_{::socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0)} {
    to_.sin_family = AF_INET;
    to_.sin_port = htons(port);
    to_.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
  }
  ~Sender() { ::close(fd_); }
  Sender(const Sender&) = delete;
  Sender& operator=(const Sender&) = delete;
  void send(std::span<const std::byte> d) const {
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast): sockets API
    ASSERT_EQ(::sendto(fd_, d.data(), d.size(), 0, reinterpret_cast<const sockaddr*>(&to_), sizeof to_),
              static_cast<ssize_t>(d.size()));
  }

 private:
  int fd_;
  sockaddr_in to_{};
};

config::UdpSettings loopback() {
  config::UdpSettings s;
  s.port = 0;  // any free port
  return s;
}

std::map<std::string, std::uint64_t> counters_of(const DetectorPort& d) {
  std::map<std::string, std::uint64_t> m;
  for (const auto& c : d.counters()) {
    m[c.name] = c.value;
  }
  return m;
}

// Reads until `n` words arrived or two seconds passed.
std::vector<std::uint64_t> read_words(DetectorPort& d, std::size_t n) {
  std::vector<std::uint64_t> out;
  std::vector<std::uint64_t> buf(4096);
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
  while (out.size() < n && std::chrono::steady_clock::now() < deadline) {
    const std::size_t got = d.read(buf);
    out.insert(out.end(), buf.begin(), buf.begin() + static_cast<std::ptrdiff_t>(got));
    if (got == 0) {
      std::this_thread::sleep_for(std::chrono::microseconds(100));  // sleep: poll
    }
  }
  return out;
}

// Reads until nothing has arrived for 50 ms, or two seconds passed.
std::vector<std::uint64_t> read_until_quiet(DetectorPort& d) {
  std::vector<std::uint64_t> out;
  std::vector<std::uint64_t> buf(4096);
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
  auto last = std::chrono::steady_clock::now();
  while (std::chrono::steady_clock::now() - last < std::chrono::milliseconds(50) &&
         std::chrono::steady_clock::now() < deadline) {
    const std::size_t got = d.read(buf);
    out.insert(out.end(), buf.begin(), buf.begin() + static_cast<std::ptrdiff_t>(got));
    if (got == 0) {
      std::this_thread::sleep_for(std::chrono::microseconds(100));  // sleep: poll
    } else {
      last = std::chrono::steady_clock::now();
    }
  }
  return out;
}

// 21 packets of a standard-MTU link; the receiver gets the first 20 in one burst.
std::vector<sim::Datagram> burst() {
  std::vector<std::uint64_t> words(21 * readout::words_per_standard_mtu);
  std::iota(words.begin(), words.end(), std::uint64_t{1});
  sim::Packetizer pk{{.source = 1}};
  return pk.packetize(words, false);
}

}  // namespace

TEST(UdpDetector, RejectsABadAddressAndReportsTheBoundPort) {
  // REQ: SRS-RDO-010
  auto bad = loopback();
  bad.address = "localhost";  // a name, not an IPv4 address
  const auto d = UdpDetector::open(bad);
  ASSERT_FALSE(d);
  EXPECT_NE(d.error().find("not an IPv4 address"), std::string::npos);
  const auto ok = UdpDetector::open(loopback());
  ASSERT_TRUE(ok) << ok.error();
  EXPECT_NE((*ok)->port(), 0);
  EXPECT_NE((*ok)->describe().find("receive buffer"), std::string::npos) << (*ok)->describe();
  EXPECT_GT(counters_of(**ok)["receive_buffer_bytes"], 0U);
  auto same = loopback();
  same.port = (*ok)->port();
  EXPECT_FALSE(UdpDetector::open(same)) << "the port is in use";
}

TEST(UdpDetector, DeliversWordsInOrderAndCountsEveryFault) {
  // REQ: SRS-RDO-007, SRS-RDO-011, SRS-DIAG-004
  const std::uint64_t began = test_support::trace_clock_ns();
  auto opened = UdpDetector::open(loopback());
  ASSERT_TRUE(opened) << opened.error();
  UdpDetector& d = **opened;
  Sender tx{d.port()};

  std::vector<std::uint64_t> words(50 * 182);
  std::iota(words.begin(), words.end(), std::uint64_t{1});
  sim::Packetizer pk{{.source = 1, .first_sequence = 0xFFFFFFF0U}};  // crosses the sequence wrap
  auto packets = pk.packetize(words, true);
  ASSERT_EQ(packets.size(), 50U);
  // Deterministic damage: drop packet 10, swap 20 and 21, send 30 twice.
  std::vector<sim::Datagram> sent;
  for (std::size_t i = 0; i < packets.size(); ++i) {
    if (i == 10) {
      continue;
    }
    if (i == 20) {
      sent.push_back(packets[21]);
      sent.push_back(packets[20]);
      ++i;
      continue;
    }
    sent.push_back(packets[i]);
    if (i == 30) {
      sent.push_back(packets[i]);
    }
  }
  const std::vector<std::byte> garbage(40, std::byte{0x55});
  tx.send(garbage);
  for (const auto& p : sent) {
    tx.send(p.bytes);
  }

  const auto got = read_words(d, words.size() - 182);
  ASSERT_EQ(got.size(), words.size() - 182);
  EXPECT_TRUE(std::is_sorted(got.begin(), got.end()));
  EXPECT_TRUE(d.end_of_stream());
  auto c = counters_of(d);
  EXPECT_EQ(c["datagrams"], sent.size() + 1);
  EXPECT_EQ(c["rejected_bad_magic"], 1U);
  EXPECT_EQ(c["packets_lost"], 1U);
  EXPECT_EQ(c["packets_reordered"], 1U);
  EXPECT_EQ(c["packets_stale"], 1U);
  EXPECT_EQ(c["packets_delivered"], 49U);
  EXPECT_EQ(c["words_delivered"], got.size());
  EXPECT_FALSE(d.fault());
  // The loss reached the flight recorder once: one packet lost now, one in total.
  const auto gaps = test_support::traced_since(began, TraceCode::link_gap);
  ASSERT_EQ(gaps.size(), 1U);
  EXPECT_EQ(gaps[0].a, 1U);
  EXPECT_EQ(gaps[0].b, 1U);
}

TEST(UdpDetector, TracesAResynchronizationOfTheLink) {
  // REQ: SRS-DIAG-004
  // A board that restarts numbers its packets anew; a jump forward of more than
  // max_gap_packets is a new numbering, not a loss, and the flight recorder keeps it.
  // Found by the coverage review of release 0.4.0: the trace had no test.
  const std::uint64_t began = test_support::trace_clock_ns();
  auto opened = UdpDetector::open(loopback());
  ASSERT_TRUE(opened) << opened.error();
  UdpDetector& d = **opened;
  Sender tx{d.port()};
  std::vector<std::uint64_t> words(5 * readout::words_per_standard_mtu);
  std::iota(words.begin(), words.end(), std::uint64_t{1});
  const auto half = std::span{words}.first(words.size() / 2);
  const auto rest = std::span{words}.subspan(words.size() / 2);
  sim::Packetizer before{{.source = 1, .first_sequence = 100}};
  sim::Packetizer after{{.source = 1, .first_sequence = 100 + (std::uint32_t{1} << 30)}};
  for (const auto& p : before.packetize(half, false)) {
    tx.send(p.bytes);
  }
  for (const auto& p : after.packetize(rest, true)) {
    tx.send(p.bytes);
  }

  const auto got = read_words(d, words.size());
  ASSERT_EQ(got.size(), words.size());
  EXPECT_TRUE(d.end_of_stream());
  auto c = counters_of(d);
  EXPECT_EQ(c["sequence_resyncs"], 1U);
  EXPECT_EQ(c["packets_lost"], 0U) << "a new numbering loses nothing";
  const auto resyncs = test_support::traced_since(began, TraceCode::link_resync);
  ASSERT_EQ(resyncs.size(), 1U);
  EXPECT_EQ(resyncs[0].a, 1U);
  EXPECT_TRUE(test_support::traced_since(began, TraceCode::link_gap).empty());
}

TEST(UdpDetector, RunsAnAcquisitionThroughTheService) {
  // REQ: SRS-RDO-012
  // The service picks the UDP adapter from the configuration; the words come
  // from the network and the link counters appear in the status report.
  AcquisitionService svc{with_default_adapters()};
  const char* cfg = R"({"schema_version": "1.1", "source": {"type": "udp", "udp": {"port": 0}},
                        "pipeline": {"max_batch_delay_us": 200}})";
  const auto parsed = config::parse_config(cfg);
  ASSERT_TRUE(parsed) << config::format_errors(parsed.error());
  ASSERT_TRUE(svc.configure(*parsed, "test").ok);
  ASSERT_TRUE(svc.start("test").ok);
  const auto status0 = svc.status();
  const std::string desc = status0["detector"];
  const auto colon = desc.find(':', desc.find("127.0.0.1"));
  const auto port = static_cast<std::uint16_t>(std::stoi(desc.substr(colon + 1)));
  Sender tx{port};

  // Time-ordered singles, as a readout link would send them.
  std::vector<std::uint64_t> words;
  for (std::int64_t i = 0; i < 20'000; ++i) {
    words.push_back(packed::encode(Single{Picoseconds{1'000'000 + i * 50'000}, CrystalId{static_cast<std::uint32_t>(i % 1000)},
                                          KeV{511.0F}}));
  }
  sim::Packetizer pk{{.source = 2}};
  for (const auto& p : pk.packetize(words, false)) {
    tx.send(p.bytes);
  }
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
  nlohmann::json st;
  do {
    std::this_thread::sleep_for(std::chrono::milliseconds(20));  // sleep: poll
    st = svc.status();
  } while (st["stages"][1]["out"].get<std::uint64_t>() < words.size() && std::chrono::steady_clock::now() < deadline);
  ASSERT_TRUE(svc.stop("test").ok);
  ASSERT_TRUE(svc.wait_for(AcqState::configured, std::chrono::seconds(5)));
  st = svc.status();
  EXPECT_EQ(st["stages"][1]["out"].get<std::uint64_t>(), words.size()) << st.dump(2);
  EXPECT_EQ(st["detector_counters"]["packets_delivered"].get<std::uint64_t>(), (words.size() + 181) / 182);
  EXPECT_EQ(st["detector_counters"]["packets_lost"].get<std::uint64_t>(), 0U);
  EXPECT_EQ(st["late_singles"].get<std::uint64_t>(), 0U);
}

TEST(UdpDetector, CountsTheDatagramsItsSocketDroppedEvenAtTheEnd) {
  // REQ: SRS-RDO-013, SRS-RDO-014
  // The smallest receive buffer the kernel allows holds a packet or two: a burst of 20 that
  // nobody reads overflows it, and the packets that arrive last are the ones dropped.
  auto s = loopback();
  s.receive_buffer_bytes = 1;
  auto opened = UdpDetector::open(s);
  ASSERT_TRUE(opened) << opened.error();
  UdpDetector& d = **opened;
  Sender tx{d.port()};
  const auto packets = burst();
  for (std::size_t i = 0; i < 20; ++i) {
    tx.send(packets[i].bytes);
  }
  (void)read_until_quiet(d);
  auto c = counters_of(d);
  const std::uint64_t delivered = c["packets_delivered"];
  EXPECT_LT(delivered, 20U);
  EXPECT_EQ(c["socket_drops"], 20U - delivered) << "every packet is delivered or dropped";
  EXPECT_EQ(c["packets_lost"], 0U) << "a loss at the end leaves no gap in the sequence";
  if (c.contains("host_udp_rcvbuf_errors")) {  // the host's counter includes other sockets'
    EXPECT_GE(c["host_udp_rcvbuf_errors"], c["socket_drops"]);
  }
  if (c.contains("nic_rx_packets")) {  // 127.0.0.1 is on the loopback interface
    EXPECT_GE(c["nic_rx_packets"], 20U);
  }

  // The next packet reveals the gap: the sequence tracker counts exactly the dropped packets.
  tx.send(packets[20].bytes);
  (void)read_until_quiet(d);
  c = counters_of(d);
  EXPECT_EQ(c["packets_lost"], 20U - delivered);
  EXPECT_EQ(c["socket_drops"], 20U - delivered);
}

TEST(UdpDetector, TheKernelsDropCountArrivesWithTheNextDatagram) {
  // REQ: SRS-RDO-013
  // Without /proc (an empty root), only SO_RXQ_OVFL tells the adapter about drops, and it
  // comes with the next datagram that the socket queues.
  auto s = loopback();
  s.receive_buffer_bytes = 1;
  auto opened = UdpDetector::open(s, ::testing::TempDir() + "no-such-root");
  ASSERT_TRUE(opened) << opened.error();
  UdpDetector& d = **opened;
  Sender tx{d.port()};
  const auto packets = burst();
  for (std::size_t i = 0; i < 20; ++i) {
    tx.send(packets[i].bytes);
  }
  (void)read_until_quiet(d);
  auto c = counters_of(d);
  const std::uint64_t delivered = c["packets_delivered"];
  ASSERT_LT(delivered, 20U);
  EXPECT_EQ(c["socket_drops"], 0U) << "no datagram has carried the count yet";
  EXPECT_FALSE(c.contains("socket_queue_bytes"));
  EXPECT_FALSE(c.contains("host_udp_rcvbuf_errors")) << "unknown, so not reported as zero";
  tx.send(packets[20].bytes);
  (void)read_until_quiet(d);
  c = counters_of(d);
  EXPECT_EQ(c["socket_drops"], 20U - delivered);
  EXPECT_EQ(c["packets_lost"], c["socket_drops"]);
}

TEST(UdpDetector, ReportsTheHostsCountersAsChangesSinceItOpened) {
  // REQ: SRS-RDO-014
  const std::filesystem::path root = ::testing::TempDir() + "udp-root-" + std::to_string(::getpid());
  std::filesystem::create_directories(root / "proc/net");
  const auto snmp = [&](int rcvbuf_errors) {
    std::ofstream{root / "proc/net/snmp"}
        << "Udp: InDatagrams NoPorts InErrors OutDatagrams RcvbufErrors SndbufErrors InCsumErrors\n"
        << "Udp: 1000 0 " << rcvbuf_errors << " 0 " << rcvbuf_errors << " 0 0\n";
  };
  snmp(117);
  {
    auto opened = UdpDetector::open(loopback(), root);
    ASSERT_TRUE(opened) << opened.error();
    snmp(120);
    auto c = counters_of(**opened);
    EXPECT_EQ(c["host_udp_rcvbuf_errors"], 3U);
    EXPECT_EQ(c["host_udp_in_errors"], 3U);
    EXPECT_EQ(c["host_udp_in_datagrams"], 0U);
    EXPECT_FALSE(c.contains("host_softnet_dropped")) << "the root has no softnet_stat";
    EXPECT_FALSE(c.contains("nic_rx_dropped")) << "the root has no interface statistics";
  }
  std::filesystem::remove_all(root);
}

TEST(UdpDetector, ASecondRunOnTheSamePortStarts) {
  // REQ: SRS-RDO-012
  // Found by the Chapter 9 measurements: the service opened the new run's
  // detector while the previous run's detector still held the port.
  std::uint16_t port = 0;
  {
    auto probe = UdpDetector::open(loopback());
    ASSERT_TRUE(probe);
    port = (*probe)->port();  // a port that was free a moment ago
  }
  AcquisitionService svc{with_default_adapters()};
  config::AcquisitionConfig c;
  c.source.type = "udp";
  c.source.udp.port = port;
  ASSERT_TRUE(svc.configure(c, "test").ok);
  for (int run = 0; run < 3; ++run) {
    const auto r = svc.start("test");
    ASSERT_TRUE(r.ok) << "run " << run << ": " << r.message;
    ASSERT_TRUE(svc.stop("test").ok);
    ASSERT_TRUE(svc.wait_for(AcqState::configured, std::chrono::seconds(5)));
  }
}
