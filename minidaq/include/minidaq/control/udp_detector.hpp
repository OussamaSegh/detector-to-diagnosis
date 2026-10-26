// SPDX-License-Identifier: MIT
// MiniDAQ - the UDP readout adapter (Chapter 9): receives MDQ-R1 packets from
// one readout link and delivers their words, in sequence order, through
// DetectorPort.
//
// What it guarantees, and what it does not:
//  - Every datagram is accounted for: delivered, held, declared lost, stale,
//    or rejected with a reason. The counters are in the status report.
//  - Words leave in sequence order, so a time-ordered link stays time-ordered
//    even when the network reorders packets (within the reorder window).
//  - Lost packets are lost: UDP does not retransmit. The DAQ counts the loss
//    and the run carries on; whether a run with loss is usable is a decision
//    for the operator and the analysis, made with the counters.
//  - Datagrams the kernel dropped because the socket's receive buffer was
//    full are counted too (socket_drops, Chapter 23), including the last ones
//    of a run, which no later sequence number reveals. The host's and the
//    network card's own drop counters are reported as changes since the
//    detector was opened (host_*, nic_*); they are host-wide, so they explain
//    a loss but do not decide whether a run is complete.
//  - One link, one source id. Merging several links into one time-ordered
//    stream is the coincidence sorter's job (Chapter 10).
#pragma once

#include <array>
#include <atomic>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "minidaq/config/acquisition_config.hpp"
#include "minidaq/control/ports.hpp"
#include "minidaq/core/expected.hpp"
#include "minidaq/format/readout_packet.hpp"
#include "minidaq/net/host_counters.hpp"

namespace minidaq::control {

class UdpDetector final : public DetectorPort {
 public:
  // Opens and binds the socket. Errors (bad address, port in use) are
  // returned, not thrown: they are configuration problems for the operator.
  // `host` reads the kernel's counters; tests give it a fake root directory.
  [[nodiscard]] static Expected<std::unique_ptr<UdpDetector>, std::string> open(
      const config::UdpSettings& s, std::filesystem::path host_root = "/");
  ~UdpDetector() override;
  UdpDetector(const UdpDetector&) = delete;
  UdpDetector& operator=(const UdpDetector&) = delete;
  UdpDetector(UdpDetector&&) = delete;
  UdpDetector& operator=(UdpDetector&&) = delete;

  std::size_t read(std::span<std::uint64_t> out) override;
  [[nodiscard]] std::optional<std::string> fault() const override;
  [[nodiscard]] std::string describe() const override { return description_; }
  [[nodiscard]] std::vector<DetectorCounter> counters() const override;

  [[nodiscard]] std::uint16_t port() const noexcept { return port_; }  // the bound port (useful with port 0)
  [[nodiscard]] bool end_of_stream() const noexcept { return end_of_stream_.load(std::memory_order_acquire); }

 private:
  UdpDetector(int fd, const config::UdpSettings& s, net::HostCounterReader host);
  void receive_batch();                      // one recvmmsg, through the tracker into pending_
  void accept(std::span<const std::byte> d);  // one datagram
  void publish_counters() noexcept;

  static constexpr std::size_t batch_datagrams = 32;

  int fd_;
  std::uint16_t port_ = 0;
  std::size_t receive_buffer_bytes_ = 0;  // what the kernel granted for data
  std::uint64_t inode_ = 0;               // the socket's, to find it in /proc/net/udp
  net::HostCounterReader host_;
  net::HostCounters host_at_open_;
  std::string description_;
  readout::SequenceTracker tracker_;
  // Ancillary data of each datagram of a batch: the socket's drop count
  // (SO_RXQ_OVFL), a 32-bit counter that the kernel attaches to every datagram.
  static constexpr std::size_t control_bytes = 64;
  std::vector<std::byte> control_;
  // One receive buffer per datagram of a batch, one byte larger than the
  // largest valid packet, so that an oversized datagram is seen as such.
  std::vector<std::byte> buffers_;
  // Words delivered by the tracker and not yet read; sized for the worst
  // case (a full batch plus a full window released at once), so it never grows.
  std::vector<std::uint64_t> pending_;
  std::size_t pending_head_ = 0;
  std::size_t pending_size_ = 0;
  std::optional<std::uint16_t> source_;  // the link's source id, from its first packet

  // Written by the reading thread, read by the control thread.
  struct Counters {
    std::atomic<std::uint64_t> datagrams{0};
    std::array<std::atomic<std::uint64_t>, readout::num_packet_errors> rejected{};
    std::atomic<std::uint64_t> other_source{0};
    std::atomic<std::uint64_t> received{0};
    std::atomic<std::uint64_t> delivered{0};
    std::atomic<std::uint64_t> reordered{0};
    std::atomic<std::uint64_t> lost{0};
    std::atomic<std::uint64_t> stale{0};
    std::atomic<std::uint64_t> resyncs{0};
    std::atomic<std::uint64_t> words{0};
    std::atomic<std::uint64_t> receive_batches{0};
    std::atomic<std::uint64_t> socket_drops{0};  // the latest SO_RXQ_OVFL value
    std::atomic<int> socket_errno{0};
  };
  std::uint64_t datagrams_ = 0;  // reader-thread copies of the counters it owns
  std::array<std::uint64_t, readout::num_packet_errors> rejected_{};
  std::uint64_t other_source_ = 0;
  std::uint64_t receive_batches_ = 0;
  std::uint64_t socket_drops_ = 0;
  std::uint64_t traced_lost_ = 0;     // the loss and resynchronization counts last recorded
  std::uint64_t traced_resyncs_ = 0;  // in the flight recorder (Chapter 21)
  Counters counters_;
  std::atomic<bool> end_of_stream_{false};
};

}  // namespace minidaq::control
