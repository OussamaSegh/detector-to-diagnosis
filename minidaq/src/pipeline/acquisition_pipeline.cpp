// SPDX-License-Identifier: MIT
#include "minidaq/pipeline/acquisition_pipeline.hpp"

#include <algorithm>
#include <limits>
#include <optional>
#include <utility>
#include <vector>

#include "minidaq/core/clock.hpp"
#include "minidaq/core/geometry.hpp"
#include "minidaq/format/packed_single.hpp"

namespace minidaq {

AcquisitionPipeline::AcquisitionPipeline(PipelineConfig cfg, WordSource source, CoincidenceSink sink)
    : cfg_{cfg},
      source_{std::move(source)},
      sink_{std::move(sink)},
      words_{cfg.batches_per_channel, cfg.batch_size},
      decoded_{cfg.batches_per_channel, cfg.batch_size},
      sorted_{cfg.batches_per_channel, cfg.batch_size},
      pairs_{cfg.batches_per_channel, cfg.batch_size},
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
  threads_[0] = std::jthread([this](std::stop_token st) { run_source(st); });
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
void AcquisitionPipeline::run_source(std::stop_token st) {
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
    if (in == nullptr) {
      if (words_.closed() && (in = words_.receive()) == nullptr) {
        break;  // closed and drained
      }
      if (in == nullptr) {
        StageStats::add(s.input_idle, 1);
        idle.pause();
        continue;
      }
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
    if (in == nullptr) {
      if (decoded_.closed() && (in = decoded_.receive()) == nullptr) {
        break;
      }
      if (in == nullptr) {
        StageStats::add(s.input_idle, 1);
        idle.pause();
        continue;
      }
    }
    idle.reset();
    Batch<Single>* out = acquire_blocking(sorted_, s);
    const std::int64_t t0 = monotonic_ns();
    std::copy_n(in->items.begin(), in->size, out->items.begin());
    out->size = in->size;
    auto v = out->view();
    std::sort(v.begin(), v.end(), time_order);
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

void AcquisitionPipeline::run_pair() {
  enter_stage(StageId::pair);
  StageStats& s = stats_of(StageId::pair);
  LatencyHistogram& lat = latency_of(StageId::pair);
  Backoff idle{cfg_.backoff};
  std::optional<Single> carry;
  std::int64_t carry_origin_ns = 0;  // origin of the batch the carried single came from
  Batch<Coincidence>* out = nullptr;
  auto flush = [&] {
    if (out != nullptr && out->size > 0) {
      StageStats::add(s.items_out, out->size);
      StageStats::add(s.batches, 1);
      pairs_.publish(out);
      out = nullptr;
    }
  };
  for (;;) {
    Batch<Single>* in = sorted_.receive();
    if (in == nullptr) {
      if (sorted_.closed() && (in = sorted_.receive()) == nullptr) {
        break;
      }
      if (in == nullptr) {
        StageStats::add(s.input_idle, 1);
        idle.pause();
        continue;
      }
    }
    idle.reset();
    const std::int64_t t0 = monotonic_ns();
    std::int64_t waited_ns = 0;
    for (const Single& x : in->view()) {
      if (carry && x.time - carry->time <= cfg_.coincidence_window) {
        if (out == nullptr) {
          const std::int64_t w0 = monotonic_ns();
          out = acquire_blocking(pairs_, s);
          waited_ns += monotonic_ns() - w0;
          out->origin_ns = carry_origin_ns;  // oldest data that went into this batch
        }
        out->push_unchecked(Coincidence{*carry, x, CoincidenceKind::prompt});
        carry.reset();
        if (out->full()) {
          flush();
        }
      } else {
        if (carry) {
          StageStats::add(s.items_filtered, 1);  // previous single found no partner
        }
        carry = x;
        carry_origin_ns = in->origin_ns;
      }
    }
    StageStats::add(s.items_in, in->size);
    sorted_.release(in);
    lat.record(monotonic_ns() - t0 - waited_ns);
    flush();  // keep latency low: never hold a partial batch across input batches
  }
  flush();
  if (carry) {
    StageStats::add(s.items_filtered, 1);  // last single of the run
  }
  pairs_.close();
  finished_stages_.fetch_add(1);
}

void AcquisitionPipeline::run_write() {
  enter_stage(StageId::write);
  StageStats& s = stats_of(StageId::write);
  LatencyHistogram& lat = latency_of(StageId::write);
  Backoff idle{cfg_.backoff};
  for (;;) {
    Batch<Coincidence>* in = pairs_.receive();
    if (in == nullptr) {
      if (pairs_.closed() && (in = pairs_.receive()) == nullptr) {
        break;
      }
      if (in == nullptr) {
        StageStats::add(s.input_idle, 1);
        idle.pause();
        continue;
      }
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
