// SPDX-License-Identifier: MIT
#include "fast_sink.hpp"

namespace ex123 {

namespace lm = minidaq::listmode;
using Clock = std::chrono::steady_clock;

FastSink::FastSink(std::unique_ptr<minidaq::control::FileOps> ops, std::string path, Options o)
    : ops_{std::move(ops)},
      path_{std::move(path)},
      opt_{o},
      block_(lm::block_bytes(o.records_per_block)),
      writer_{block_, o.records_per_block} {
  for (std::size_t i = 1; i < opt_.buffers; ++i) {
    spare_.emplace_back(block_.size());
  }
  const auto fd = ops_->create(path_);
  if (!fd) {
    fail("create", fd.error());
    closed_ = true;
    return;
  }
  fd_ = *fd;
  write_all(lm::encode_file_header(R"({"format":"MDQ-L1"})"));
  io_ = std::thread{&FastSink::io_loop, this};
}

FastSink::~FastSink() {
  if (!closed_) {
    (void)close();
  }
  if (io_.joinable()) {
    io_.join();
  }
}

void FastSink::fail(const std::string& what, int err) {
  const std::lock_guard lock{mu_};
  if (fault_.empty()) {
    fault_ = what + " " + path_ + ": " + minidaq::control::errno_message(err);
  }
}

std::optional<std::string> FastSink::fault() const {
  const std::lock_guard lock{mu_};
  return fault_.empty() ? std::nullopt : std::optional<std::string>{fault_};
}

void FastSink::write_all(std::span<const std::byte> data) {
  while (!data.empty()) {
    const auto n = ops_->write(fd_, data);
    if (!n) {
      return fail("write", n.error());
    }
    data = data.subspan(*n);
  }
}

// [snippet:handoff]
// The caller's thread only encodes and swaps buffers; the disk is the I/O
// thread's business.
void FastSink::hand_off(bool last) {
  if (writer_.records() > 0 || last) {
    block_.resize(writer_.finish(sequence_++, last ? lm::block_flag_end_of_run : 0U));
    std::unique_lock lock{mu_};
    queue_.push_back(std::move(block_));
    last_queued_ = last;
    cv_.notify_one();
    if (last) {
      return;
    }
    spare_cv_.wait(lock, [&] { return !spare_.empty(); });  // backpressure, never loss
    block_ = std::move(spare_.back());
    spare_.pop_back();
  }
  writer_.reset(block_);
}
// [/snippet:handoff]

void FastSink::write(std::span<const minidaq::Coincidence> batch) {
  if (closed_) {
    return;
  }
  for (const auto& c : batch) {
    auto r = writer_.append(c);
    if (r == lm::BlockWriter::Append::invalid) {
      continue;
    }
    if (r != lm::BlockWriter::Append::ok) {
      hand_off(false);
      r = writer_.append(c);
    }
  }
}

// [snippet:io]
// Writes blocks as they come and calls fsync when the oldest unsynced data
// is max_unsynced old: one fsync covers many blocks, so its cost is shared,
// and the time bound holds at any rate.
void FastSink::io_loop() {
  std::optional<Clock::time_point> unsynced_since;
  while (true) {
    std::vector<std::byte> block;
    bool last = false;
    {
      std::unique_lock lock{mu_};
      const auto ready = [&] { return !queue_.empty() || last_queued_; };
      if (unsynced_since) {
        cv_.wait_until(lock, *unsynced_since + opt_.max_unsynced, ready);
      } else {
        cv_.wait(lock, ready);
      }
      if (!queue_.empty()) {
        block = std::move(queue_.front());
        queue_.pop_front();
      }
      last = queue_.empty() && last_queued_;
    }
    if (!block.empty()) {
      if (!fault()) {
        write_all(block);
        if (!unsynced_since) {
          unsynced_since = Clock::now();
        }
      }
      block.resize(lm::block_bytes(opt_.records_per_block));
      {
        const std::lock_guard lock{mu_};
        spare_.push_back(std::move(block));
      }
      spare_cv_.notify_one();
    }
    if (unsynced_since && (last || Clock::now() - *unsynced_since >= opt_.max_unsynced) && !fault()) {
      if (const int e = ops_->sync(fd_); e != 0) {
        fail("fsync", e);
      }
      unsynced_since.reset();
    }
    if (last) {
      return;
    }
  }
}
// [/snippet:io]

std::optional<std::string> FastSink::close() {
  if (closed_) {
    return fault();
  }
  closed_ = true;
  hand_off(true);
  io_.join();
  if (const int e = ops_->close(fd_); e != 0) {
    fail("close", e);
  }
  return fault();
}

}  // namespace ex123
