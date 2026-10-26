// SPDX-License-Identifier: MIT
// MiniDAQ - the host's own counters of the receive path (Chapter 23).
//
// A datagram can be dropped at four places between the wire and MiniDAQ, and Linux counts each
// one somewhere else:
//  - the network card, when its receive ring is full (rx_missed_errors, rx_fifo_errors) or the
//    driver throws the frame away (rx_dropped): /sys/class/net/IF/statistics;
//  - the per-CPU backlog of the receive softirq (dropped), and the softirq that ran out of its
//    budget before the queue was empty (time_squeeze): /proc/net/softnet_stat;
//  - the UDP layer, when a socket's receive buffer is full (RcvbufErrors, also counted in
//    InErrors) or no socket has the port (NoPorts): the "Udp:" lines of /proc/net/snmp;
//  - and the one socket that is MiniDAQ's: the drops column of /proc/net/udp.
// These functions parse those files. They are pure (text in, numbers out) so that every format
// is tested with captured text; HostCounterReader reads the files below a root directory, so
// that tests can give it a fake one.
#pragma once

#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace minidaq::net {

// [snippet:counters]
struct UdpCounters {  // /proc/net/snmp, whole host, since boot
  std::uint64_t in_datagrams = 0;
  std::uint64_t no_ports = 0;
  std::uint64_t in_errors = 0;
  std::uint64_t rcvbuf_errors = 0;
  std::uint64_t in_csum_errors = 0;
};

struct SoftnetCounters {  // /proc/net/softnet_stat, summed over the CPUs; 32-bit, they wrap
  std::uint64_t processed = 0;
  std::uint64_t dropped = 0;
  std::uint64_t time_squeeze = 0;
};

struct InterfaceCounters {  // /sys/class/net/IF/statistics, one network interface
  std::uint64_t rx_packets = 0;
  std::uint64_t rx_dropped = 0;
  std::uint64_t rx_missed_errors = 0;
  std::uint64_t rx_fifo_errors = 0;
};

struct SocketState {                 // one line of /proc/net/udp
  std::uint64_t rx_queue_bytes = 0;  // waiting in the receive buffer now
  std::uint64_t drops = 0;           // dropped since the socket was created; 32-bit
};
// [/snippet:counters]

[[nodiscard]] std::optional<UdpCounters> parse_snmp_udp(std::string_view snmp);
[[nodiscard]] std::optional<SoftnetCounters> parse_softnet_stat(std::string_view softnet_stat);
// The socket whose inode is `inode` (fstat on the socket's descriptor gives it).
[[nodiscard]] std::optional<SocketState> parse_proc_net_udp(std::string_view proc_net_udp,
                                                            std::uint64_t inode);

struct HostCounters {
  std::optional<UdpCounters> udp;
  std::optional<SoftnetCounters> softnet;
  std::optional<InterfaceCounters> nic;  // only when the interface is known
};

// What changed between two readings, as named counters: host_udp_*, host_softnet_*, nic_*.
// A counter that either reading lacks is left out rather than reported as zero, because a
// zero would claim that nothing was dropped. The softnet counters are 32-bit and are
// subtracted modulo 2^32.
[[nodiscard]] std::vector<std::pair<std::string, std::uint64_t>> difference(
    const HostCounters& now, const HostCounters& before);

class HostCounterReader {
 public:
  // `root` is "/" on a real system; `interface` is empty when the receiving interface is not
  // known (a socket bound to 0.0.0.0 receives on all of them).
  explicit HostCounterReader(std::filesystem::path root = "/", std::string interface = {});
  [[nodiscard]] HostCounters read() const;
  [[nodiscard]] std::optional<SocketState> socket(std::uint64_t inode) const;
  [[nodiscard]] const std::string& interface() const noexcept { return interface_; }

 private:
  std::filesystem::path root_;
  std::string interface_;
};

}  // namespace minidaq::net
