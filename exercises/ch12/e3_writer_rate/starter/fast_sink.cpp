// SPDX-License-Identifier: MIT
#include "fast_sink.hpp"

namespace ex123 {

namespace lm = minidaq::listmode;

FastSink::FastSink(std::unique_ptr<minidaq::control::FileOps> ops, std::string path, Options o)
    : ops_{std::move(ops)},
      path_{std::move(path)},
      opt_{o},
      block_(lm::block_bytes(o.records_per_block)),
      writer_{block_, o.records_per_block} {
  const auto fd = ops_->create(path_);
  if (!fd) {
    fault_ = "create " + path_ + ": " + minidaq::control::errno_message(fd.error());
    closed_ = true;
    return;
  }
  fd_ = *fd;
  write_all(lm::encode_file_header(R"({"format":"MDQ-L1"})"));
}

FastSink::~FastSink() {
  if (!closed_) {
    (void)close("");
  }
}

void FastSink::write_all(std::span<const std::byte> data) {
  while (!data.empty() && fault_.empty()) {
    const auto n = ops_->write(fd_, data);
    if (!n) {
      fault_ = "write " + path_ + ": " + minidaq::control::errno_message(n.error());
      return;
    }
    data = data.subspan(*n);
  }
}

void FastSink::flush_block(bool last) {
  const auto bytes = writer_.finish(sequence_++, last ? lm::block_flag_end_of_run : 0U);
  write_all(std::span{block_}.first(bytes));
  // Durable before the next block: safe, and one fsync per 64 KiB.
  if (fault_.empty()) {
    if (const int e = ops_->sync(fd_); e != 0) {
      fault_ = "fsync " + path_ + ": " + minidaq::control::errno_message(e);
    }
  }
  writer_.reset();
}

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
      flush_block(false);
      r = writer_.append(c);
    }
  }
}

std::optional<std::string> FastSink::close(std::string_view /*run_record*/) {
  if (closed_) {
    return fault();
  }
  closed_ = true;
  flush_block(true);
  if (const int e = ops_->close(fd_); e != 0 && fault_.empty()) {
    fault_ = "close " + path_ + ": " + minidaq::control::errno_message(e);
  }
  return fault();
}

}  // namespace ex123
