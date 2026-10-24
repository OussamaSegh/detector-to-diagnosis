// SPDX-License-Identifier: MIT
#include "minidaq/pipeline/acquisition_pipeline.hpp"

#include <algorithm>
#include <limits>
#include <utility>
#include <vector>

#include "minidaq/core/clock.hpp"
#include "minidaq/core/geometry.hpp"
#include "minidaq/format/packed_single.hpp"

namespace minidaq {

AcquisitionPipeline::AcquisitionPipeline(const PipelineConfig& cfg, WordSource source, CoincidenceSink sink)
    : cfg_{cfg},
      source_{std::move(source)},
      sink_{std::move(sink)},
      words_{cfg.batches_per_channel, cfg.batch_size},
      decoded_{cfg.batches_per_channel, cfg.batch_size},
      sorted_{cfg.batches_per_channel, cfg.batch_size},
      pairs_{cfg.batches_per_channel, cfg.batch_size},
      sorter_{std::make_unique<CoincidenceSorter>(cfg.sorter)},
      end_to_end_{std::make_unique<LatencyHistogram>()} {
  for (auto& h : stage_latency_) {
    h = std::make_unique<LatencyHistogram>();
  }
}

AcquisitionPipeline::~AcquisitionPipeline() {
  request_stop();
  wait();
}

void AcquisitionPipeline::start() {
  if (cfg_.rt.lock_memory) {
    // Before the threads start, so their stacks are locked too (MCL_FUTURE).
    memory_locked_ = rt::lock_all_memory().has_value();
  }
  // Start consumers first so the source never sees a pipeline without readers.
  threads_[4] = std::jthread([this] { run_write(); });
  threads_[3] = std::jthread([this] { run_pair(); });
  threads_[2] = std::jthread([this] { run_sort(); });
  threads_[1] = std::jthread([this] { run_decode(); });
  threads_[0] = std::jthread([this](const std::stop_token& st) { run_source(st); });
  ready_.wait();  // every stage has applied its settings and written rt_status_
}

// [snippet:enter]
// First thing every stage thread does: name itself, apply its real-time
// settings, record what happened, and count down the start latch.
void AcquisitionPipeline::enter_stage(StageId id) noexcept {
  static constexpr std::array<const char*, num_stages> names{"mdq-source", "mdq-decode", "mdq-sort", "mdq-pair",
                                                             "mdq-write"};
  const auto i = static_cast<std::size_t>(id);
  rt::name_current_thread(names[i]);
  rt_status_[i] = rt::apply_stage(cfg_.rt.stages[i], cfg_.rt.prefault_stack_bytes);
  ready_.count_down();  // publishes rt_status_[i] to start()
}
// [/snippet:enter]

void AcquisitionPipeline::request_stop() noexcept { threads_[0].request_stop(); }

void AcquisitionPipeline::wait() {
  for (auto& t : threads_) {
    if (t.joinable()) {
      t.join();
    }
  }
}

std::array<StageSnapshot, num_stages> AcquisitionPipeline::stats() const noexcept {
  return {snapshot("source", stats_[0]), snapshot("decode", stats_[1]), snapshot("sort", stats_[2]),
          snapshot("pair", stats_[3]), snapshot("write", stats_[4])};
}

std::size_t AcquisitionPipeline::want_words(std::uint64_t produced) const noexcept {
  if (cfg_.total_words == 0) {
    return cfg_.batch_size;
  }
  return static_cast<std::size_t>(std::min<std::uint64_t>(cfg_.batch_size, cfg_.total_words - produced));
}

template <typename T>
Batch<T>* AcquisitionPipeline::acquire_blocking(Channel<T>& ch, StageStats& s) {
  Backoff backoff{cfg_.backoff};
  Batch<T>* b = ch.acquire();
  if (b == nullptr) {
    StageStats::add(s.output_stalls, 1);
    while ((b = ch.acquire()) == nullptr) {
      backoff.pause();
    }
  }
  return b;
}

// [snippet:source]
void AcquisitionPipeline::run_source(const std::stop_token& st) {
  enter_stage(StageId::source);
  StageStats& s = stats_of(StageId::source);
  LatencyHistogram& lat = latency_of(StageId::source);
  std::vector<std::uint64_t> scratch(cfg_.batch_size);  // where dropped data goes
  Backoff backoff{cfg_.backoff};
  const std::int64_t max_delay_ns = cfg_.max_batch_delay.count();
  std::uint64_t produced = 0;
  Batch<std::uint64_t>* b = nullptr;  // batch being filled
  std::int64_t busy_ns = 0;           // time spent reading into b

  auto publish = [&] {
    StageStats::add(s.items_out, b->size);
    StageStats::add(s.batches, 1);
    lat.record(busy_ns);
    words_.publish(b);
    b = nullptr;
    busy_ns = 0;
  };

  while (!st.stop_requested() && (cfg_.total_words == 0 || produced < cfg_.total_words)) {
    if (b == nullptr) {
      b = words_.acquire();
      if (b == nullptr && cfg_.source_overflow == OverflowPolicy::drop) {
        // The "hardware" does not wait: read the data and throw it away, counted.
        const std::size_t n = source_(std::span(scratch).first(want_words(produced)));
        produced += n;
        StageStats::add(s.items_in, n);
        StageStats::add(s.items_dropped, n);
        if (n == 0) {
          backoff.pause();
        }
        continue;
      }
      if (b == nullptr) {
        StageStats::add(s.output_stalls, 1);
        while (!st.stop_requested() && (b = words_.acquire()) == nullptr) {
          backoff.pause();  // back-pressure: the source waits for the pipeline
        }
        backoff.reset();
        if (b == nullptr) {
          break;
        }
      }
    }
    // Fill the batch until it is full or its oldest word has waited max_batch_delay.
    const std::size_t room = std::min(b->capacity() - b->size, want_words(produced));
    const std::int64_t t0 = monotonic_ns();
    const std::size_t n = source_(std::span(b->items).subspan(b->size, room));
    const std::int64_t t1 = monotonic_ns();
    if (n > 0) {
      if (b->size == 0) {
        // The oldest data in this batch: when it was due if the source knows, else now.
        b->origin_ns = cfg_.due_time_ns ? std::min(t0, cfg_.due_time_ns(produced)) : t0;
      }
      b->size += n;
      produced += n;
      busy_ns += t1 - t0;
      StageStats::add(s.items_in, n);
      backoff.reset();
    }
    if (b->full() || (b->size > 0 && t1 - b->origin_ns >= max_delay_ns)) {
      publish();
    } else if (n == 0) {
      backoff.pause();
    }
  }
  if (b != nullptr && b->size > 0) {
    publish();  // never lose a partial batch at stop
  } else if (b != nullptr) {
    words_.release_unused(b);
  }
  words_.close();
  finished_stages_.fetch_add(1);
}
// [/snippet:source]

// [snippet:decode]
void AcquisitionPipeline::run_decode() {
  enter_stage(StageId::decode);
  StageStats& s = stats_of(StageId::decode);
  LatencyHistogram& lat = latency_of(StageId::decode);
  packed::StreamDecoder decoder{ScannerGeometry::num_crystals};
  Backoff idle{cfg_.backoff};
  for (;;) {
    Batch<std::uint64_t>* in = words_.receive();
    if (in == nullptr && words_.closed()) {
      in = words_.receive();  // a batch published just before the close
      if (in == nullptr) {
        break;  // closed and drained
      }
    }
    if (in == nullptr) {
      StageStats::add(s.input_idle, 1);
      idle.pause();
      continue;
    }
    idle.reset();
    Batch<Single>* out = acquire_blocking(decoded_, s);
    const std::int64_t t0 = monotonic_ns();  // service time excludes waiting
    out->size = decoder.decode(in->view(), out->items);
    out->origin_ns = in->origin_ns;
    lat.record(monotonic_ns() - t0);
    StageStats::add(s.items_in, in->size);
    StageStats::add(s.items_out, out->size);
    StageStats::add(s.items_filtered, in->size - out->size);  // invalid words, counted
    StageStats::add(s.batches, 1);
    words_.release(in);
    decoded_.publish(out);
  }
  decoded_.close();
  finished_stages_.fetch_add(1);
}
// [/snippet:decode]

void AcquisitionPipeline::run_sort() {
  enter_stage(StageId::sort);
  StageStats& s = stats_of(StageId::sort);
  LatencyHistogram& lat = latency_of(StageId::sort);
  Backoff idle{cfg_.backoff};
  Picoseconds last_emitted{std::numeric_limits<std::int64_t>::min()};
  for (;;) {
    Batch<Single>* in = decoded_.receive();
    if (in == nullptr && decoded_.closed()) {
      in = decoded_.receive();  // a batch published just before the close
      if (in == nullptr) {
        break;  // closed and drained
      }
    }
    if (in == nullptr) {
      StageStats::add(s.input_idle, 1);
      idle.pause();
      continue;
    }
    idle.reset();
    Batch<Single>* out = acquire_blocking(sorted_, s);
    const std::int64_t t0 = monotonic_ns();
    std::copy_n(in->items.begin(), in->size, out->items.begin());
    out->size = in->size;
    auto v = out->view();
    std::sort(v.begin(), v.end(), TimeOrder{});  // a function object, so the comparison inlines
    if (!v.empty()) {
      // Singles older than what we already emitted cannot be fixed here.
      const auto late = static_cast<std::uint64_t>(std::count_if(
          v.begin(), v.end(), [&](const Single& x) { return x.time < last_emitted; }));
      late_singles_.fetch_add(late, std::memory_order_relaxed);
      last_emitted = std::max(last_emitted, v.back().time);
    }
    out->origin_ns = in->origin_ns;
    lat.record(monotonic_ns() - t0);
    StageStats::add(s.items_in, in->size);
    StageStats::add(s.items_out, out->size);
    StageStats::add(s.batches, 1);
    decoded_.release(in);
    sorted_.publish(out);
  }
  sorted_.close();
  finished_stages_.fetch_add(1);
}

namespace {

// The SorterStats fields, in one place, for copying to and from the atomics.
constexpr std::uint64_t SorterStats::*sorter_members[] = {
    &SorterStats::singles_in,       &SorterStats::energy_rejected,      &SorterStats::out_of_order,
    &SorterStats::singles_alone,    &SorterStats::pair_windows,         &SorterStats::multiple_windows,
    &SorterStats::singles_in_multiples, &SorterStats::geometry_rejected, &SorterStats::prompts,
    &SorterStats::prompts_from_multiples, &SorterStats::delayed};

// Which input batch a single came from, by data time, so that an output batch
// carries the origin (arrival time) of the oldest data in it. The sorter holds
// singles across batches, so this is not simply the current input batch.
class OriginTrack {
 public:
  void add(Picoseconds last_time, std::int64_t origin_ns) noexcept {
    if (n_ == ring_.size()) {
      pop();  // more batches than the sorter could still hold: forget the oldest
    }
    ring_[(head_ + n_) % ring_.size()] = {last_time, origin_ns};
    ++n_;
  }
  // Origin of the batch holding a single at time t (the oldest batch if t is older).
  [[nodiscard]] std::int64_t origin_of(Picoseconds t) const noexcept {
    for (std::size_t i = 0; i < n_; ++i) {
      const Entry& e = ring_[(head_ + i) % ring_.size()];
      if (e.last_time >= t) {
        return e.origin_ns;
      }
    }
    return n_ > 0 ? ring_[(head_ + n_ - 1) % ring_.size()].origin_ns : 0;
  }
  // Forgets batches whose singles are all older than t.
  void drop_before(Picoseconds t) noexcept {
    while (n_ > 1 && ring_[head_].last_time < t) {
      pop();
    }
  }
  void clear() noexcept { n_ = 0; }

 private:
  struct Entry {
    Picoseconds last_time{};
    std::int64_t origin_ns = 0;
  };
  void pop() noexcept {
    head_ = (head_ + 1) % ring_.size();
    --n_;
  }
  std::array<Entry, 256> ring_{};
  std::size_t head_ = 0;
  std::size_t n_ = 0;
};

}  // namespace

SorterStats AcquisitionPipeline::sorter_stats() const noexcept {
  static_assert(std::size(sorter_members) == sorter_fields, "one atomic per SorterStats field");
  SorterStats st;
  for (std::size_t i = 0; i < sorter_fields; ++i) {
    st.*sorter_members[i] = sorter_stats_[i].load(std::memory_order_relaxed);
  }
  return st;
}

// [snippet:pair]
void AcquisitionPipeline::run_pair() {
  enter_stage(StageId::pair);
  StageStats& s = stats_of(StageId::pair);
  LatencyHistogram& lat = latency_of(StageId::pair);
  Backoff idle{cfg_.backoff};
  CoincidenceSorter& sorter = *sorter_;
  std::vector<Coincidence> found;
  found.reserve(2 * cfg_.batch_size);  // take_all_goods can find more pairs than singles
  OriginTrack origins;
  std::uint64_t removed_before = 0;
  // Copies what the sorter found into output batches; returns the time spent
  // waiting for free batches, which is not the stage's own work.
  auto publish = [&] {
    std::int64_t waited_ns = 0;
    std::size_t i = 0;
    while (i < found.size()) {
      const std::int64_t w0 = monotonic_ns();
      Batch<Coincidence>* out = acquire_blocking(pairs_, s);
      waited_ns += monotonic_ns() - w0;
      out->origin_ns = origins.origin_of(found[i].first.time);  // the oldest data in this batch
      const std::size_t n = std::min(out->capacity(), found.size() - i);
      std::copy_n(found.begin() + static_cast<std::ptrdiff_t>(i), n, out->items.begin());
      out->size = n;
      i += n;
      StageStats::add(s.items_out, n);
      StageStats::add(s.batches, 1);
      pairs_.publish(out);
    }
    found.clear();
    const SorterStats& st = sorter.stats();
    for (std::size_t f = 0; f < sorter_fields; ++f) {
      sorter_stats_[f].store(st.*sorter_members[f], std::memory_order_relaxed);
    }
    // Singles removed before windowing (energy gate, order) are "filtered".
    const std::uint64_t removed = st.energy_rejected + st.out_of_order;
    StageStats::add(s.items_filtered, removed - removed_before);
    removed_before = removed;
    return waited_ns;
  };
  for (;;) {
    Batch<Single>* in = sorted_.receive();
    if (in == nullptr && sorted_.closed()) {
      in = sorted_.receive();  // a batch published just before the close
      if (in == nullptr) {
        break;  // closed and drained
      }
    }
    if (in == nullptr) {
      StageStats::add(s.input_idle, 1);
      idle.pause();
      continue;
    }
    idle.reset();
    const std::int64_t t0 = monotonic_ns();
    if (in->size > 0) {
      origins.add(in->view().back().time, in->origin_ns);
    }
    sorter.push(in->view(), found);
    StageStats::add(s.items_in, in->size);
    sorted_.release(in);
    const std::int64_t waited_ns = publish();  // never hold coincidences across input batches
    if (sorter.held() == 0) {
      origins.clear();
    } else {
      origins.drop_before(sorter.oldest_held_time());
    }
    lat.record(monotonic_ns() - t0 - waited_ns);
  }
  sorter.flush(found);  // end of the run: close every open window
  (void)publish();
  pairs_.close();
  finished_stages_.fetch_add(1);
}
// [/snippet:pair]

void AcquisitionPipeline::run_write() {
  enter_stage(StageId::write);
  StageStats& s = stats_of(StageId::write);
  LatencyHistogram& lat = latency_of(StageId::write);
  Backoff idle{cfg_.backoff};
  for (;;) {
    Batch<Coincidence>* in = pairs_.receive();
    if (in == nullptr && pairs_.closed()) {
      in = pairs_.receive();  // a batch published just before the close
      if (in == nullptr) {
        break;  // closed and drained
      }
    }
    if (in == nullptr) {
      StageStats::add(s.input_idle, 1);
      idle.pause();
      continue;
    }
    idle.reset();
    const std::int64_t t0 = monotonic_ns();
    if (sink_) {
      sink_(in->view());
    }
    const std::int64_t t1 = monotonic_ns();
    lat.record(t1 - t0);
    end_to_end_->record(t1 - in->origin_ns);
    StageStats::add(s.items_in, in->size);
    StageStats::add(s.items_out, in->size);
    StageStats::add(s.batches, 1);
    pairs_.release(in);
  }
  finished_stages_.fetch_add(1);
}

}  // namespace minidaq
