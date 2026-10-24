// SPDX-License-Identifier: MIT
#include "minidaq/pipeline/acquisition_pipeline.hpp"

#include <algorithm>
#include <limits>
#include <optional>
#include <utility>
#include <vector>

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
      pairs_{cfg.batches_per_channel, cfg.batch_size} {}

AcquisitionPipeline::~AcquisitionPipeline() {
  request_stop();
  wait();
}

void AcquisitionPipeline::start() {
  // Start consumers first so the source never sees a pipeline without readers.
  threads_[4] = std::jthread([this] { run_write(); });
  threads_[3] = std::jthread([this] { run_pair(); });
  threads_[2] = std::jthread([this] { run_sort(); });
  threads_[1] = std::jthread([this] { run_decode(); });
  threads_[0] = std::jthread([this](std::stop_token st) { run_source(st); });
}

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
  StageStats& s = stats_of(StageId::source);
  std::vector<std::uint64_t> scratch(cfg_.batch_size);  // where dropped data goes
  Backoff backoff{cfg_.backoff};
  std::uint64_t produced = 0;
  while (!st.stop_requested() && (cfg_.total_words == 0 || produced < cfg_.total_words)) {
    const std::size_t want = cfg_.total_words == 0
                                 ? cfg_.batch_size
                                 : static_cast<std::size_t>(std::min<std::uint64_t>(cfg_.batch_size, cfg_.total_words - produced));
    Batch<std::uint64_t>* b = words_.acquire();
    if (b == nullptr) {
      if (cfg_.source_overflow == OverflowPolicy::drop) {
        // The "hardware" does not wait: read the data and throw it away, counted.
        const std::size_t n = source_(std::span(scratch).first(want));
        if (n == 0) {
          backoff.pause();
          continue;
        }
        produced += n;
        StageStats::add(s.items_in, n);
        StageStats::add(s.items_dropped, n);
        continue;
      }
      StageStats::add(s.output_stalls, 1);
      while (!st.stop_requested() && (b = words_.acquire()) == nullptr) {
        backoff.pause();  // back-pressure: the source waits for the pipeline
      }
      backoff.reset();
      if (b == nullptr) {
        break;
      }
    }
    const std::size_t n = source_(std::span(b->items).first(want));
    if (n == 0) {
      words_.release_unused(b);
      backoff.pause();
      continue;
    }
    b->size = n;
    produced += n;
    StageStats::add(s.items_in, n);
    StageStats::add(s.items_out, n);
    StageStats::add(s.batches, 1);
    words_.publish(b);
  }
  words_.close();
  finished_stages_.fetch_add(1);
}
// [/snippet:source]

// [snippet:decode]
void AcquisitionPipeline::run_decode() {
  StageStats& s = stats_of(StageId::decode);
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
    out->size = decoder.decode(in->view(), out->items);
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
  StageStats& s = stats_of(StageId::sort);
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
  StageStats& s = stats_of(StageId::pair);
  Backoff idle{cfg_.backoff};
  std::optional<Single> carry;
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
    for (const Single& x : in->view()) {
      if (carry && x.time - carry->time <= cfg_.coincidence_window) {
        if (out == nullptr) {
          out = acquire_blocking(pairs_, s);
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
      }
    }
    StageStats::add(s.items_in, in->size);
    sorted_.release(in);
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
  StageStats& s = stats_of(StageId::write);
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
    if (sink_) {
      sink_(in->view());
    }
    StageStats::add(s.items_in, in->size);
    StageStats::add(s.items_out, in->size);
    StageStats::add(s.batches, 1);
    pairs_.release(in);
  }
  finished_stages_.fetch_add(1);
}

}  // namespace minidaq
