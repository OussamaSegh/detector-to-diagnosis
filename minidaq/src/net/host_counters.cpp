// SPDX-License-Identifier: MIT
#include "minidaq/net/host_counters.hpp"

#include <charconv>
#include <fstream>
#include <iterator>

namespace minidaq::net {

namespace {

// The whitespace-separated fields of one line.
std::vector<std::string_view> fields(std::string_view line) {
  std::vector<std::string_view> out;
  std::size_t i = 0;
  while (i < line.size()) {
    while (i < line.size() && (line[i] == ' ' || line[i] == '\t')) {
      ++i;
    }
    const std::size_t start = i;
    while (i < line.size() && line[i] != ' ' && line[i] != '\t') {
      ++i;
    }
    if (i > start) {
      out.push_back(line.substr(start, i - start));
    }
  }
  return out;
}

std::vector<std::string_view> lines(std::string_view text) {
  std::vector<std::string_view> out;
  while (!text.empty()) {
    const std::size_t nl = text.find('\n');
    out.push_back(text.substr(0, nl));
    text = nl == std::string_view::npos ? std::string_view{} : text.substr(nl + 1);
  }
  return out;
}

std::optional<std::uint64_t> number(std::string_view s, int base = 10) {
  std::uint64_t v = 0;
  const auto [ptr, ec] = std::from_chars(s.data(), s.data() + s.size(), v, base);
  if (s.empty() || ec != std::errc{} || ptr != s.data() + s.size()) {
    return std::nullopt;
  }
  return v;
}

std::optional<std::string> slurp(const std::filesystem::path& p) {
  std::ifstream in{p};
  if (!in) {
    return std::nullopt;
  }
  return std::string{std::istreambuf_iterator<char>{in}, std::istreambuf_iterator<char>{}};
}

std::uint64_t minus(std::uint64_t now, std::uint64_t before) {
  return now >= before ? now - before : 0;  // a counter that went back was reset: no change
}

std::uint64_t minus32(std::uint64_t now, std::uint64_t before) {
  return (now - before) & 0xFFFF'FFFFU;
}

}  // namespace

// [snippet:snmp]
// /proc/net/snmp holds pairs of lines for each protocol: the names, then the values.
//   Udp: InDatagrams NoPorts InErrors OutDatagrams RcvbufErrors SndbufErrors InCsumErrors ...
//   Udp: 74507 0 0 74507 0 0 0 0 0
// The columns are found by name, because kernels add columns over the years.
std::optional<UdpCounters> parse_snmp_udp(std::string_view snmp) {
  std::vector<std::string_view> names;
  for (const std::string_view line : lines(snmp)) {
    if (!line.starts_with("Udp:")) {
      continue;
    }
    const auto f = fields(line);
    if (names.empty()) {
      names = f;
      continue;
    }
    if (f.size() != names.size()) {
      return std::nullopt;
    }
    UdpCounters c;
    int found = 0;
    for (std::size_t i = 1; i < f.size(); ++i) {
      const auto v = number(f[i]);
      if (!v) {
        return std::nullopt;
      }
      for (const auto& [name, field] : {std::pair{"InDatagrams", &c.in_datagrams},
                                        {"NoPorts", &c.no_ports},
                                        {"InErrors", &c.in_errors},
                                        {"RcvbufErrors", &c.rcvbuf_errors},
                                        {"InCsumErrors", &c.in_csum_errors}}) {
        if (names[i] == name) {
          *field = *v;
          ++found;
        }
      }
    }
    return found == 5 ? std::optional{c} : std::nullopt;
  }
  return std::nullopt;
}
// [/snippet:snmp]

// One line per CPU, hexadecimal: processed, dropped, time_squeeze, then columns this parser
// does not need.
std::optional<SoftnetCounters> parse_softnet_stat(std::string_view softnet_stat) {
  SoftnetCounters c;
  int cpus = 0;
  for (const std::string_view line : lines(softnet_stat)) {
    const auto f = fields(line);
    if (f.empty()) {
      continue;
    }
    if (f.size() < 3) {
      return std::nullopt;
    }
    const auto processed = number(f[0], 16);
    const auto dropped = number(f[1], 16);
    const auto squeeze = number(f[2], 16);
    if (!processed || !dropped || !squeeze) {
      return std::nullopt;
    }
    c.processed += *processed;
    c.dropped += *dropped;
    c.time_squeeze += *squeeze;
    ++cpus;
  }
  return cpus > 0 ? std::optional{c} : std::nullopt;
}

// [snippet:proc-net-udp]
//  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
//   ref pointer drops
//  12: 0100007F:1E15 00000000:0000 07 00000000:00000000 00:00000000 00000000  1000        0 81234
//   2 0000000000000000 0
// (one line per socket; the addresses and queues are hexadecimal, inode and drops decimal)
std::optional<SocketState> parse_proc_net_udp(std::string_view proc_net_udp, std::uint64_t inode) {
  for (const std::string_view line : lines(proc_net_udp)) {
    const auto f = fields(line);
    if (f.size() < 13 || f[0] == "sl" || number(f[9]) != inode) {
      continue;
    }
    const std::string_view queues = f[4];  // tx_queue:rx_queue
    const std::size_t colon = queues.find(':');
    const auto rx_queue =
        colon == std::string_view::npos ? std::nullopt : number(queues.substr(colon + 1), 16);
    const auto drops = number(f[12]);
    if (!rx_queue || !drops) {
      return std::nullopt;
    }
    return SocketState{*rx_queue, *drops};
  }
  return std::nullopt;
}
// [/snippet:proc-net-udp]

std::vector<std::pair<std::string, std::uint64_t>> difference(const HostCounters& now,
                                                              const HostCounters& before) {
  std::vector<std::pair<std::string, std::uint64_t>> out;
  if (now.udp && before.udp) {
    const UdpCounters &a = *now.udp, &b = *before.udp;
    out.emplace_back("host_udp_in_datagrams", minus(a.in_datagrams, b.in_datagrams));
    out.emplace_back("host_udp_no_ports", minus(a.no_ports, b.no_ports));
    out.emplace_back("host_udp_in_errors", minus(a.in_errors, b.in_errors));
    out.emplace_back("host_udp_rcvbuf_errors", minus(a.rcvbuf_errors, b.rcvbuf_errors));
    out.emplace_back("host_udp_in_csum_errors", minus(a.in_csum_errors, b.in_csum_errors));
  }
  if (now.softnet && before.softnet) {
    const SoftnetCounters &a = *now.softnet, &b = *before.softnet;
    out.emplace_back("host_softnet_dropped", minus32(a.dropped, b.dropped));
    out.emplace_back("host_softnet_time_squeeze", minus32(a.time_squeeze, b.time_squeeze));
  }
  if (now.nic && before.nic) {
    const InterfaceCounters &a = *now.nic, &b = *before.nic;
    out.emplace_back("nic_rx_packets", minus(a.rx_packets, b.rx_packets));
    out.emplace_back("nic_rx_dropped", minus(a.rx_dropped, b.rx_dropped));
    out.emplace_back("nic_rx_missed_errors", minus(a.rx_missed_errors, b.rx_missed_errors));
    out.emplace_back("nic_rx_fifo_errors", minus(a.rx_fifo_errors, b.rx_fifo_errors));
  }
  return out;
}

HostCounterReader::HostCounterReader(std::filesystem::path root, std::string interface)
    : root_{std::move(root)}, interface_{std::move(interface)} {}

HostCounters HostCounterReader::read() const {
  HostCounters c;
  if (const auto text = slurp(root_ / "proc/net/snmp")) {
    c.udp = parse_snmp_udp(*text);
  }
  if (const auto text = slurp(root_ / "proc/net/softnet_stat")) {
    c.softnet = parse_softnet_stat(*text);
  }
  // An interface name comes from the kernel (getifaddrs), never from a path the operator
  // typed, but a name with a slash or "." and ".." would still leave the directory.
  if (!interface_.empty() && interface_.find('/') == std::string::npos && interface_ != "." &&
      interface_ != "..") {
    const auto dir = root_ / "sys/class/net" / interface_ / "statistics";
    InterfaceCounters n;
    bool ok = true;
    for (const auto& [file, field] : {std::pair{"rx_packets", &n.rx_packets},
                                      {"rx_dropped", &n.rx_dropped},
                                      {"rx_missed_errors", &n.rx_missed_errors},
                                      {"rx_fifo_errors", &n.rx_fifo_errors}}) {
      const auto text = slurp(dir / file);
      std::optional<std::uint64_t> v;
      if (text) {
        std::string_view t{*text};
        while (!t.empty() && (t.back() == '\n' || t.back() == ' ')) {
          t.remove_suffix(1);
        }
        v = number(t);
      }
      if (!v) {
        ok = false;
        break;
      }
      *field = *v;
    }
    if (ok) {
      c.nic = n;
    }
  }
  return c;
}

std::optional<SocketState> HostCounterReader::socket(std::uint64_t inode) const {
  const auto text = slurp(root_ / "proc/net/udp");
  return text ? parse_proc_net_udp(*text, inode) : std::nullopt;
}

}  // namespace minidaq::net
