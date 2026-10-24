// SPDX-License-Identifier: MIT
// Exercise 3.3 solution: four threads, three Channels, per-stage reports.
#include "pipeline.hpp"

#include <algorithm>
#include <optional>
#include <thread>

#include "minidaq/core/geometry.hpp"
#include "minidaq/format/packed_single.hpp"
#include "minidaq/pipeline/acquisition_pipeline.hpp"  // time_order
#include "minidaq/pipeline/backoff.hpp"
#include "minidaq/pipeline/channel.hpp"

namespace ex {
namespace {

using Clock = std::chrono::steady_clock;
using minidaq::Batch;
using minidaq::Channel;
using minidaq::Coincidence;
using minidaq::Single;

double seconds(Clock::duration d) { return std::chrono::duration<double>(d).count(); }

// Waits for an empty batch (back-pressure).
template <typename T>
Batch<T>* acquire_wait(Channel<T>& ch) {
  minidaq::Backoff b;
  Batch<T>* out = nullptr;
  while ((out = ch.acquire()) == nullptr) {
    b.pause();
  }
  return out;
}

// Returns the next full batch, or nullptr once the channel is closed and drained.
template <typename T>
Batch<T>* receive_wait(Channel<T>& ch) {
  minidaq::Backoff b;
  for (;;) {
    if (Batch<T>* in = ch.receive()) {
      return in;
    }
    if (ch.closed()) {
      return ch.receive();  // anything published before close()
    }
    b.pause();
  }
}

}  // namespace

Result run_pipeline(std::span<const std::uint64_t> words, const Config& cfg, const WriteCallback& on_write) {
  Result r;
  r.stages = {StageReport{"decode"}, StageReport{"sort"}, StageReport{"pair"}, StageReport{"write"}};
  auto& [dec, srt, par, wri] = r.stages;

  Channel<Single> decoded{cfg.queue_batches, cfg.batch_size};
  Channel<Single> sorted{cfg.queue_batches, cfg.batch_size};
  Channel<Coincidence> pairs{cfg.queue_batches, cfg.batch_size};
  r.coincidences.reserve(words.size() / 2);

  const auto t0 = Clock::now();
  {
    std::jthread writer([&] {
      while (Batch<Coincidence>* in = receive_wait(pairs)) {
        const auto t = Clock::now();
        if (cfg.write_delay.count() > 0) {
          std::this_thread::sleep_for(cfg.write_delay);
        }
        if (on_write) {
          on_write(in->view());
        }
        r.coincidences.insert(r.coincidences.end(), in->view().begin(), in->view().end());
        wri.in += in->size;
        wri.out += in->size;
        wri.busy_seconds += seconds(Clock::now() - t);
        pairs.release(in);
      }
    });
    std::jthread pairer([&] {
      std::optional<Single> carry;
      while (Batch<Single>* in = receive_wait(sorted)) {
        Batch<Coincidence>* out = acquire_wait(pairs);  // at most size/2 pairs fit
        const auto t = Clock::now();
        for (const Single& x : in->view()) {
          if (carry && x.time - carry->time <= cfg.window) {
            out->push_unchecked(Coincidence{*carry, x, minidaq::CoincidenceKind::prompt});
            carry.reset();
          } else {
            par.filtered += carry ? 1U : 0U;  // the previous single found no partner
            carry = x;
          }
        }
        par.in += in->size;
        par.out += out->size;
        par.busy_seconds += seconds(Clock::now() - t);
        sorted.release(in);
        if (out->size > 0) {
          pairs.publish(out);
        } else {
          pairs.release_unused(out);
        }
      }
      par.filtered += carry ? 1U : 0U;
      pairs.close();
    });
    std::jthread sorter([&] {
      while (Batch<Single>* in = receive_wait(decoded)) {
        Batch<Single>* out = acquire_wait(sorted);
        const auto t = Clock::now();
        std::copy_n(in->items.begin(), in->size, out->items.begin());
        out->size = in->size;
        auto v = out->view();
        std::sort(v.begin(), v.end(), minidaq::time_order);
        srt.in += in->size;
        srt.out += out->size;
        srt.busy_seconds += seconds(Clock::now() - t);
        decoded.release(in);
        sorted.publish(out);
      }
      sorted.close();
    });
    std::jthread decoder([&] {
      minidaq::packed::StreamDecoder d{minidaq::ScannerGeometry::num_crystals};
      for (std::size_t pos = 0; pos < words.size(); pos += cfg.batch_size) {
        const auto chunk = words.subspan(pos, std::min(cfg.batch_size, words.size() - pos));
        Batch<Single>* out = decoded.acquire();
        if (out == nullptr) {
          if (cfg.overflow == Overflow::drop) {
            dec.in += chunk.size();
            dec.dropped += chunk.size();
            continue;
          }
          out = acquire_wait(decoded);
        }
        const auto t = Clock::now();
        out->size = d.decode(chunk, out->items);
        dec.in += chunk.size();
        dec.out += out->size;
        dec.filtered += chunk.size() - out->size;
        dec.busy_seconds += seconds(Clock::now() - t);
        decoded.publish(out);
      }
      decoded.close();
    });
  }  // jthreads join here, in reverse order of construction
  r.wall_seconds = seconds(Clock::now() - t0);
  return r;
}

}  // namespace ex
