// SPDX-License-Identifier: MIT
// Exercise 12.3: a list-mode sink that keeps up with the sorter on a disk
// whose fsync is slow, and still bounds how much data a power cut can take.
#pragma once

#include <chrono>
#include <cstddef>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "minidaq/control/file_ops.hpp"
#include "minidaq/control/ports.hpp"
#include "minidaq/format/list_mode.hpp"

namespace ex123 {

struct Options {
  std::size_t records_per_block = 4096;
  // Data handed to the file may wait at most this long for an fsync. The
  // number to put in the design: what a power cut can take.
  std::chrono::milliseconds max_unsynced{100};
  // Blocks between the encoder and the disk; when all are in use, write()
  // waits (backpressure) instead of growing without bound.
  std::size_t buffers = 32;
};

// Writes one MDQ-L1 file. write() is called by the pipeline's writer thread
// and must not wait for the disk; close() ends the run and makes it durable.
//
// TODO(12.3): this version is correct and durable, and far too slow: it
// writes and fsyncs every block on the caller's thread. Keep its guarantees
// (nothing lost, everything durable at close, a fault on a failed write) and
// make write() independent of the disk's latency. You may change everything
// below the public interface.
class FastSink final : public minidaq::control::CoincidenceSinkPort {
 public:
  FastSink(std::unique_ptr<minidaq::control::FileOps> ops, std::string path, Options o = {});
  ~FastSink() override;
  FastSink(const FastSink&) = delete;
  FastSink& operator=(const FastSink&) = delete;
  FastSink(FastSink&&) = delete;
  FastSink& operator=(FastSink&&) = delete;

  void write(std::span<const minidaq::Coincidence> batch) override;
  [[nodiscard]] std::optional<std::string> close() override;
  [[nodiscard]] std::optional<std::string> fault() const override { return fault_.empty() ? std::nullopt : std::optional<std::string>{fault_}; }
  [[nodiscard]] std::string describe() const override { return "exercise 12.3 sink: " + path_; }

 private:
  void flush_block(bool last);
  void write_all(std::span<const std::byte> data);

  std::unique_ptr<minidaq::control::FileOps> ops_;
  std::string path_;
  Options opt_;
  int fd_ = -1;
  std::vector<std::byte> block_;
  minidaq::listmode::BlockWriter writer_;
  std::uint32_t sequence_ = 0;
  bool closed_ = false;
  std::string fault_;
};

}  // namespace ex123
