// SPDX-License-Identifier: MIT
// MiniDAQ - the threaded acquisition pipeline (Chapter 3).
//
//   source --words--> decode --singles--> sort --singles--> pair --coincidences--> write
//
// Five threads connected by four Channels (SPSC rings of pre-allocated
// batches). Every stage counts what it receives, emits and drops. The source
// is where data enters from "hardware": when the pipeline is full it either
// applies back-pressure (blocks, as a TCP link or a FIFO with flow control
// would) or drops whole batches and counts every lost word, as a UDP link
// would. Downstream stages always block: losing data inside the PC silently
// is never acceptable (Chapter 15).
//
// Chapter 3 versions of sort and pair are deliberately simple placeholders:
// sort reorders within a batch and counts singles older than the last one
// emitted; pair takes non-overlapping pairs of consecutive singles within the
// window. Chapter 10 replaces both with the real coincidence sorter.
#pragma once

#include <array>
#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <latch>
#include <memory>
#include <span>
#include <thread>

#include "minidaq/core/single.hpp"
#include "minidaq/pipeline/backoff.hpp"
#include "minidaq/pipeline/channel.hpp"
#include "minidaq/metrics/latency_histogram.hpp"
#include "minidaq/pipeline/stage_stats.hpp"
#include "minidaq/rt/realtime.hpp"

namespace minidaq {

enum class OverflowPolicy : std::uint8_t { block, drop };

struct PipelineConfig {
  std::size_t batch_size = 4096;
  std::size_t batches_per_channel = 64;
  Picoseconds coincidence_window{4'000};
  OverflowPolicy source_overflow = OverflowPolicy::block;
  std::uint64_t total_words = 0;  // stop after this many words (0: run until stopped)
  // A partially filled batch is sent once its oldest word is this old: bounds
  // latency at low rates, while full batches keep overhead low at high rates.
  std::chrono::nanoseconds max_batch_delay{std::chrono::microseconds{500}};
  BackoffPolicy backoff{};
  rt::RtProfile rt{};  // pinning, scheduling, memory locking (Chapter 4); default: none
  // Optional: when word number `index` (from 0) was due to arrive, in monotonic
  // ns. A source that knows its schedule (sim::PacedSource) supplies it, so
  // latency is measured from when data should have arrived rather than from
  // when the source got around to reading it; without it, a stalled source
  // hides its own backlog (coordinated omission, Chapter 4). Source thread only.
  std::function<std::int64_t(std::uint64_t index)> due_time_ns;
};

// [snippet:order]
// Total order used by the sort stage. Time alone is not enough: MDQ-P1 has a
// 5 ps resolution, so ties are common at high rates, and std::sort is not
// stable. Breaking ties by crystal makes the output a pure function of the
// input, which is what reproducible runs (and regression tests) need.
[[nodiscard]] constexpr bool time_order(const Single& a, const Single& b) noexcept {
  if (a.time != b.time) {
    return a.time < b.time;
  }
  return a.crystal < b.crystal;
}
// [/snippet:order]

enum class StageId : std::uint8_t { source = 0, decode, sort, pair, write };
inline constexpr std::size_t num_stages = 5;

class AcquisitionPipeline {
 public:
  // Called on the source thread to fill a buffer with packed words; returns
  // how many it wrote (0 means "no data right now").
  using WordSource = std::function<std::size_t(std::span<std::uint64_t>)>;
  // Called on the writer thread for each batch of coincidences. Must not throw.
  using CoincidenceSink = std::function<void(std::span<const Coincidence>)>;

  AcquisitionPipeline(PipelineConfig cfg, WordSource source, CoincidenceSink sink);
  ~AcquisitionPipeline();
  AcquisitionPipeline(const AcquisitionPipeline&) = delete;
  AcquisitionPipeline& operator=(const AcquisitionPipeline&) = delete;

  // Starts the stages and returns once every stage thread has applied its
  // real-time settings, so rt_status() is complete when start() returns.
  void start();
  // Asks the source to stop; the other stages drain what is in flight.
  void request_stop() noexcept;
  // Blocks until every stage has finished.
  void wait();
  [[nodiscard]] bool finished() const noexcept { return finished_stages_.load() == num_stages; }

  [[nodiscard]] std::array<StageSnapshot, num_stages> stats() const noexcept;
  [[nodiscard]] std::uint64_t late_singles() const noexcept { return late_singles_.load(std::memory_order_relaxed); }

  // Per-stage service time of each batch, in ns (time spent processing, not waiting).
  [[nodiscard]] const LatencyHistogram& stage_latency(StageId id) const noexcept {
    return *stage_latency_[static_cast<std::size_t>(id)];
  }
  // Time from a batch entering the PC (source) to its coincidences being written, in ns.
  [[nodiscard]] const LatencyHistogram& end_to_end_latency() const noexcept { return *end_to_end_; }
  // Valid after start() returns.
  [[nodiscard]] const std::array<rt::StageRtStatus, num_stages>& rt_status() const noexcept { return rt_status_; }
  [[nodiscard]] bool memory_locked() const noexcept { return memory_locked_; }

 private:
  void run_source(std::stop_token st);
  void run_decode();
  void run_sort();
  void run_pair();
  void run_write();
  template <typename T>
  Batch<T>* acquire_blocking(Channel<T>& ch, StageStats& s);
  [[nodiscard]] std::size_t want_words(std::uint64_t produced) const noexcept;
  StageStats& stats_of(StageId id) noexcept { return stats_[static_cast<std::size_t>(id)]; }
  LatencyHistogram& latency_of(StageId id) noexcept { return *stage_latency_[static_cast<std::size_t>(id)]; }
  void enter_stage(StageId id) noexcept;

  PipelineConfig cfg_;
  WordSource source_;
  CoincidenceSink sink_;
  Channel<std::uint64_t> words_;
  Channel<Single> decoded_;
  Channel<Single> sorted_;
  Channel<Coincidence> pairs_;
  std::array<StageStats, num_stages> stats_{};
  alignas(cache_line_size) std::atomic<std::uint64_t> late_singles_{0};
  std::atomic<std::size_t> finished_stages_{0};
  std::array<std::unique_ptr<LatencyHistogram>, num_stages> stage_latency_;
  std::unique_ptr<LatencyHistogram> end_to_end_;
  std::array<rt::StageRtStatus, num_stages> rt_status_{};  // each written by its own stage before ready_
  bool memory_locked_ = false;
  std::latch ready_{num_stages};
  std::array<std::jthread, num_stages> threads_{};
};

}  // namespace minidaq
