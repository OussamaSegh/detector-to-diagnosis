// SPDX-License-Identifier: MIT
// The host's receive-path counters (Chapter 23): each file format from captured text, the
// differences between two readings, and the reader over a fake root directory.
#include <gtest/gtest.h>
#include <unistd.h>

#include <filesystem>
#include <fstream>
#include <map>
#include <string>

#include "minidaq/net/host_counters.hpp"

using namespace minidaq::net;

namespace {

// Captured from Ubuntu 24.04 (kernel 6.8): the Udp lines have nine columns there.
constexpr const char* snmp_text =
    "Ip: Forwarding DefaultTTL InReceives InHdrErrors\n"
    "Ip: 2 64 468004 0\n"
    "Udp: InDatagrams NoPorts InErrors OutDatagrams RcvbufErrors SndbufErrors InCsumErrors "
    "IgnoredMulti MemErrors\n"
    "Udp: 74507 3 120 74511 117 0 2 0 0\n"
    "UdpLite: InDatagrams NoPorts InErrors OutDatagrams RcvbufErrors SndbufErrors InCsumErrors "
    "IgnoredMulti MemErrors\n"
    "UdpLite: 0 0 0 0 0 0 0 0 0\n";

constexpr const char* softnet_text =
    "00058a57 00000000 00000002 00000000 00000000 00000000 00000000 00000000 00000000 00000000 "
    "00000000 00000000 00000000\n"
    "0000ffff 00000010 00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000 "
    "00000000 00000000 00000001\n";

constexpr const char* udp_text =
    "   sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  "
    "timeout inode ref pointer drops\n"
    "  341: 00000000:A6E1 00000000:0000 07 00000000:00000000 00:00000000 00000000     0        "
    "0 20714 2 0000000000000000 0\n"
    "  500: 0100007F:1E15 00000000:0000 07 00000000:00012A00 00:00000000 00000000  1000        "
    "0 81234 2 0000000000000000 117\n";

std::map<std::string, std::uint64_t> as_map(
    const std::vector<std::pair<std::string, std::uint64_t>>& v) {
  return {v.begin(), v.end()};
}

// A directory tree that looks like / to HostCounterReader.
class FakeRoot {
 public:
  FakeRoot() : root_{::testing::TempDir() + "hostroot-" + std::to_string(::getpid())} {
    std::filesystem::create_directories(root_ / "proc/net");
    std::filesystem::create_directories(root_ / "sys/class/net/eth1/statistics");
  }
  ~FakeRoot() { std::filesystem::remove_all(root_); }
  FakeRoot(const FakeRoot&) = delete;
  FakeRoot& operator=(const FakeRoot&) = delete;
  FakeRoot(FakeRoot&&) = delete;
  FakeRoot& operator=(FakeRoot&&) = delete;
  void write(const std::string& path, const std::string& text) const {
    std::ofstream{root_ / path} << text;
  }
  [[nodiscard]] const std::filesystem::path& path() const { return root_; }

 private:
  std::filesystem::path root_;
};

}  // namespace

TEST(HostCounters, ReadsTheUdpCountersByColumnName) {
  // REQ: SRS-RDO-014
  const auto c = parse_snmp_udp(snmp_text);
  ASSERT_TRUE(c);
  EXPECT_EQ(c->in_datagrams, 74'507U);
  EXPECT_EQ(c->no_ports, 3U);
  EXPECT_EQ(c->in_errors, 120U);
  EXPECT_EQ(c->rcvbuf_errors, 117U);
  EXPECT_EQ(c->in_csum_errors, 2U);
  // An older kernel without InCsumErrors, with the columns in another order: found by name.
  EXPECT_FALSE(parse_snmp_udp("Udp: InDatagrams NoPorts InErrors RcvbufErrors\nUdp: 1 2 3 4\n"))
      << "a column that is missing is not taken as zero";
  const auto moved = parse_snmp_udp(
      "Udp: RcvbufErrors InCsumErrors InDatagrams NoPorts InErrors\nUdp: 4 5 1 2 3\n");
  ASSERT_TRUE(moved);
  EXPECT_EQ(moved->rcvbuf_errors, 4U);
  EXPECT_EQ(moved->in_datagrams, 1U);
  EXPECT_FALSE(parse_snmp_udp("Udp: InDatagrams NoPorts\nUdp: 1\n")) << "a short line";
  EXPECT_FALSE(parse_snmp_udp("Udp: InDatagrams NoPorts\nUdp: 1 x\n")) << "not a number";
  EXPECT_FALSE(parse_snmp_udp("Ip: 1 2\n")) << "no Udp lines";
}

TEST(HostCounters, SumsTheBacklogCountersOfEveryCpu) {
  // REQ: SRS-RDO-014
  const auto c = parse_softnet_stat(softnet_text);
  ASSERT_TRUE(c);
  EXPECT_EQ(c->processed, 0x58a57U + 0xffffU);
  EXPECT_EQ(c->dropped, 0x10U);
  EXPECT_EQ(c->time_squeeze, 3U);
  EXPECT_FALSE(parse_softnet_stat(""));
  EXPECT_FALSE(parse_softnet_stat("0000 zz 0000\n"));
  EXPECT_FALSE(parse_softnet_stat("0000 0000\n"));
}

TEST(HostCounters, FindsOneSocketByItsInode) {
  // REQ: SRS-RDO-013
  const auto s = parse_proc_net_udp(udp_text, 81'234);
  ASSERT_TRUE(s);
  EXPECT_EQ(s->drops, 117U);
  EXPECT_EQ(s->rx_queue_bytes, 0x12A00U);
  EXPECT_EQ(parse_proc_net_udp(udp_text, 20'714)->drops, 0U);
  EXPECT_FALSE(parse_proc_net_udp(udp_text, 99)) << "no such socket";
  EXPECT_FALSE(parse_proc_net_udp("", 81'234));
}

TEST(HostCounters, ReportsOnlyWhatBothReadingsHave) {
  // REQ: SRS-RDO-014
  HostCounters before{UdpCounters{100, 0, 5, 5, 0}, SoftnetCounters{10, 0xFFFF'FFFEU, 1},
                      std::nullopt};
  HostCounters after{UdpCounters{300, 1, 9, 8, 0}, SoftnetCounters{20, 3, 4},
                     InterfaceCounters{1000, 1, 2, 3}};
  auto d = as_map(difference(after, before));
  EXPECT_EQ(d["host_udp_in_datagrams"], 200U);
  EXPECT_EQ(d["host_udp_rcvbuf_errors"], 3U);
  EXPECT_EQ(d["host_udp_in_errors"], 4U);
  EXPECT_EQ(d["host_udp_no_ports"], 1U);
  EXPECT_EQ(d["host_softnet_dropped"], 5U) << "the 32-bit counter wrapped";
  EXPECT_EQ(d["host_softnet_time_squeeze"], 3U);
  EXPECT_FALSE(d.contains("nic_rx_dropped")) << "the first reading had no interface";
  before.udp.reset();
  EXPECT_FALSE(as_map(difference(after, before)).contains("host_udp_rcvbuf_errors"));
}

TEST(HostCounters, ReadsTheFilesBelowARoot) {
  // REQ: SRS-RDO-014
  const FakeRoot root;
  root.write("proc/net/snmp", snmp_text);
  root.write("proc/net/softnet_stat", softnet_text);
  root.write("proc/net/udp", udp_text);
  for (const char* f : {"rx_packets", "rx_dropped", "rx_missed_errors", "rx_fifo_errors"}) {
    root.write(std::string{"sys/class/net/eth1/statistics/"} + f, "7\n");
  }
  const HostCounterReader reader{root.path(), "eth1"};
  const HostCounters c = reader.read();
  ASSERT_TRUE(c.udp);
  EXPECT_EQ(c.udp->rcvbuf_errors, 117U);
  ASSERT_TRUE(c.softnet);
  ASSERT_TRUE(c.nic);
  EXPECT_EQ(c.nic->rx_missed_errors, 7U);
  EXPECT_EQ(reader.socket(81'234)->drops, 117U);

  EXPECT_FALSE(HostCounterReader(root.path(), "eth2").read().nic) << "no such interface";
  EXPECT_FALSE(HostCounterReader(root.path(), "../eth1").read().nic) << "a name is not a path";
  EXPECT_FALSE(HostCounterReader(root.path()).read().nic);
  root.write("sys/class/net/eth1/statistics/rx_dropped", "many\n");
  EXPECT_FALSE(reader.read().nic) << "one unreadable counter, and the interface is not reported";
  const HostCounters none = HostCounterReader(root.path() / "missing").read();
  EXPECT_FALSE(none.udp || none.softnet || none.nic);
}
