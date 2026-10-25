// SPDX-License-Identifier: MIT
// MiniDAQ - the list-mode file sink (Chapter 12): writes the coincidences of
// a run to MDQ-L1 files (minidaq/format/list_mode.hpp).
//
// Two threads share the work. The pipeline's writer thread calls write() and
// encodes records straight into block buffers from a fixed pool; full blocks
// go to the sink's own I/O thread, which writes them, calls fsync as the
// policy says, and returns the buffers. Nothing is allocated per block.
//
// What it guarantees:
//  - Backpressure, not loss. When the disk is slower than the data, the pool
//    runs dry and write() waits for a buffer; the pipeline's queues fill and
//    only the source, which is where the overflow policy is decided, can drop
//    (Chapter 2). The sink itself never drops a coincidence while it is
//    healthy. Its waits are counted.
//  - Bounded data at risk. A block is handed to the I/O thread when it is full
//    or max_block_delay after its first record, whichever is first; with the
//    fsync policy "interval", at most fsync_every_blocks blocks are written
//    but not yet on stable storage.
//  - Crash-safe files. A file is written as <name>.mdql.part and renamed to
//    <name>.mdql only after its last block and an fsync (unless the policy is
//    "none"), followed by an fsync of the directory. A file without .part is
//    complete; a .part file is what a crash left, readable up to its last
//    complete block.
//  - Rotation. A file ends before it would exceed max_file_bytes; every file
//    ends with an empty closing block that says whether the run continues in
//    the next file or ends here.
//  - The run's record goes with the data. close() stores the caller's record
//    of the run (the service's counters, the link's losses) and the sink's
//    own counters in <prefix>-<run_name>.run.json, so a file set says how
//    it was acquired without the DAQ's logs.
//  - Failure is a fault, not a silent loss. A failed write, fsync or rename
//    (a full disk, an I/O error) makes fault() report it; the service stops
//    the run. Blocks after a fault are counted as dropped.
#pragma once

#include <array>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <vector>

#include <nlohmann/json.hpp>

#include "minidaq/control/file_ops.hpp"
#include "minidaq/control/ports.hpp"
#include "minidaq/core/expected.hpp"
#include "minidaq/format/list_mode.hpp"

namespace minidaq::control {

enum class FsyncPolicy : std::uint8_t {
  none,      // never: the page cache decides when data reaches the disk
  close,     // once per file, before the rename
  interval,  // also every fsync_every_blocks blocks
};

// [snippet:config]
struct ListModeSinkConfig {
  std::string directory = ".";
  std::string prefix = "minidaq";
  std::string run_name;           // files are <prefix>-<run_name>-<NNNN>.mdql; required
  nlohmann::json metadata;        // written into every file's header, with the file's segment number
  std::uint64_t max_file_bytes = std::uint64_t{1} << 30;
  std::size_t records_per_block = 4096;  // 64 KiB blocks
  std::size_t buffers = 64;              // blocks in flight between encoder and disk
  FsyncPolicy fsync = FsyncPolicy::close;
  std::uint32_t fsync_every_blocks = 256;  // policy "interval": 16 MiB with the default block
  std::chrono::milliseconds max_block_delay{100};
};
// [/snippet:config]

// [snippet:stats]
struct ListModeSinkStats {
  std::uint64_t coincidences = 0;      // records written to blocks
  std::uint64_t invalid = 0;           // coincidences the format cannot hold (never expected)
  std::uint64_t time_resets = 0;       // a coincidence earlier than the one before it
  std::uint64_t energies_clamped = 0;  // energies outside 0 .. 2048 keV
  std::uint64_t blocks = 0;            // blocks written (not counting closing blocks)
  std::uint64_t bytes = 0;             // bytes written, headers included
  std::uint64_t files = 0;             // files completed and renamed
  std::uint64_t buffer_waits = 0;      // times write() waited for a free buffer (backpressure)
  std::uint64_t buffer_wait_ns = 0;    // total time it waited
  std::uint64_t fsyncs = 0;           // of segments and of the run record
  std::uint64_t max_fsync_ns = 0;
  std::uint64_t max_write_ns = 0;      // the slowest write of one block
  std::uint64_t blocks_dropped = 0;    // after a fault
};
// [/snippet:stats]

class ListModeSink final : public CoincidenceSinkPort {
 public:
  // Checks the configuration, creates the first file and starts the I/O
  // thread. Errors (no such directory, the file exists) are returned.
  [[nodiscard]] static Expected<std::unique_ptr<ListModeSink>, std::string> open(ListModeSinkConfig cfg,
                                                                                 std::unique_ptr<FileOps> ops);
  ~ListModeSink() override;  // close("") if it was not called
  ListModeSink(const ListModeSink&) = delete;
  ListModeSink& operator=(const ListModeSink&) = delete;
  ListModeSink(ListModeSink&&) = delete;
  ListModeSink& operator=(ListModeSink&&) = delete;

  void write(std::span<const Coincidence> batch) override;
  // Flushes the last block, ends the run's last file and waits for the I/O
  // thread, then writes the run record, <prefix>-<run_name>.run.json: the
  // files, the sink's counters and run_record (the caller's JSON, kept as
  // text if it does not parse), made durable like a segment. Only once;
  // later calls return the same result.
  [[nodiscard]] std::optional<std::string> close(std::string_view run_record) override;
  [[nodiscard]] std::optional<std::string> fault() const override;
  [[nodiscard]] std::string describe() const override;
  [[nodiscard]] std::vector<DetectorCounter> counters() const override;

  [[nodiscard]] ListModeSinkStats stats() const;
  // Completed files, in order (full paths).
  [[nodiscard]] std::vector<std::string> files() const;

 private:
  // What the encoder hands to the I/O thread.
  struct Item {
    int buffer = -1;              // -1: no block, only the actions below
    std::size_t bytes = 0;
    bool new_file_before = false;      // first close the current file and open the next one
    std::uint32_t rotate_sequence = 0;  // the closing block's sequence number in the file that ends
    bool end_of_run = false;            // after the block, end the run's last file ...
    std::uint32_t final_sequence = 0;   // ... with a closing block of this sequence number
  };

  ListModeSink(ListModeSinkConfig cfg, std::unique_ptr<FileOps> ops);
  [[nodiscard]] std::optional<std::string> open_file();  // I/O thread, or open() before it starts
  void finish_file(std::uint32_t sequence, std::uint32_t flags);
  void write_bytes(std::span<const std::byte> data);
  void write_run_record(std::string_view run_record);
  void set_fault(std::string message);
  [[nodiscard]] bool faulted() const noexcept { return faulted_.load(std::memory_order_acquire); }
  [[nodiscard]] std::string part_path(std::uint32_t segment) const;
  void submit(bool end_of_run);  // encoder: hand off the current block
  void io_loop();
  [[nodiscard]] std::size_t header_bytes_for(std::uint32_t segment) const;

  ListModeSinkConfig cfg_;
  std::unique_ptr<FileOps> ops_;
  std::vector<std::vector<std::byte>> pool_;

  // Encoder state (writer thread only).
  int current_ = -1;
  listmode::BlockWriter writer_;
  std::uint32_t sequence_ = 0;        // of the next block in the current file
  std::uint64_t file_bytes_ = 0;      // the current file's size once its queued blocks are written
  std::uint32_t encoder_segment_ = 0;  // the file the encoder is filling
  std::chrono::steady_clock::time_point block_started_;
  bool closed_ = false;
  std::optional<std::string> close_result_;

  // Shared between the two threads.
  mutable std::mutex mu_;
  std::condition_variable free_cv_;
  std::condition_variable full_cv_;
  std::deque<int> free_;
  std::deque<Item> full_;
  std::string fault_;
  std::vector<std::string> files_;
  std::atomic<bool> faulted_{false};

  // I/O thread state.
  int fd_ = -1;
  std::uint32_t segment_ = 0;
  std::uint32_t blocks_since_sync_ = 0;
  std::array<std::byte, listmode::block_header_bytes> closing_{};

  // Counters, written by one thread each and read by any.
  struct Counters {
    std::atomic<std::uint64_t> coincidences{0}, invalid{0}, time_resets{0}, energies_clamped{0}, blocks{0},
        bytes{0}, files{0}, buffer_waits{0}, buffer_wait_ns{0}, fsyncs{0}, max_fsync_ns{0}, max_write_ns{0},
        blocks_dropped{0};
  } n_;

  std::thread io_;  // last: it starts after everything above exists
};

// The sink for configuration section /output (schema 1.3) with type
// "listmode": the run name is the UTC start time, the metadata the effective
// configuration and the scanner geometry.
[[nodiscard]] std::unique_ptr<CoincidenceSinkPort> make_listmode_sink(const config::AcquisitionConfig& c,
                                                                      std::string& error);

}  // namespace minidaq::control
