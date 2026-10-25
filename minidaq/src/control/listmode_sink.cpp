// SPDX-License-Identifier: MIT
#include "minidaq/control/listmode_sink.hpp"

#include <algorithm>
#include <cstdio>

#include "minidaq/control/audit.hpp"
#include "minidaq/core/geometry.hpp"

namespace minidaq::control {

namespace {

using Clock = std::chrono::steady_clock;

std::uint64_t ns_since(Clock::time_point t0) {
  return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now() - t0).count());
}

void store_max(std::atomic<std::uint64_t>& a, std::uint64_t v) noexcept {
  std::uint64_t cur = a.load(std::memory_order_relaxed);
  while (v > cur && !a.compare_exchange_weak(cur, v, std::memory_order_relaxed)) {
  }
}

std::string_view to_string(FsyncPolicy p) noexcept {
  switch (p) {
    case FsyncPolicy::none: return "none";
    case FsyncPolicy::close: return "close";
    case FsyncPolicy::interval: return "interval";
  }
  return "unknown";
}

}  // namespace

ListModeSink::ListModeSink(ListModeSinkConfig cfg, std::unique_ptr<FileOps> ops)
    : cfg_{std::move(cfg)},
      ops_{std::move(ops)},
      pool_(cfg_.buffers, std::vector<std::byte>(listmode::block_bytes(cfg_.records_per_block))),
      current_{0},
      writer_{pool_[0], cfg_.records_per_block},
      file_bytes_{header_bytes_for(0)},
      block_started_{Clock::now()} {
  for (int i = 1; i < static_cast<int>(pool_.size()); ++i) {
    free_.push_back(i);
  }
}

Expected<std::unique_ptr<ListModeSink>, std::string> ListModeSink::open(ListModeSinkConfig cfg,
                                                                         std::unique_ptr<FileOps> ops) {
  auto bad_name = [](const std::string& s) { return s.empty() || s.find('/') != std::string::npos; };
  if (bad_name(cfg.run_name) || bad_name(cfg.prefix)) {
    return Unexpected<std::string>{"prefix and run name must be non-empty and contain no '/'"};
  }
  if (cfg.records_per_block == 0 || cfg.records_per_block > listmode::max_block_records) {
    return Unexpected<std::string>{"records_per_block must be in 1 .. 65536"};
  }
  if (cfg.buffers < 2 || cfg.buffers > 65536) {
    return Unexpected<std::string>{"buffers must be in 2 .. 65536"};
  }
  if (cfg.fsync_every_blocks == 0) {
    return Unexpected<std::string>{"fsync_every_blocks must be at least 1"};
  }
  if (cfg.max_block_delay.count() <= 0) {
    return Unexpected<std::string>{"max_block_delay must be positive"};
  }
  if (!cfg.metadata.is_object()) {
    return Unexpected<std::string>{"metadata must be a JSON object"};
  }
  if (ops == nullptr) {
    return Unexpected<std::string>{"no file operations"};
  }
  // NOLINTNEXTLINE(cppcoreguidelines-owning-memory): the constructor is private, so no make_unique
  std::unique_ptr<ListModeSink> s{new ListModeSink{std::move(cfg), std::move(ops)}};
  // A file must hold its header, one full block and its closing block.
  const auto least = s->header_bytes_for(9999) + listmode::block_bytes(s->cfg_.records_per_block) +
                     listmode::block_header_bytes;
  if (s->cfg_.max_file_bytes < least) {
    s->closed_ = true;  // nothing to flush: the I/O thread never started
    return Unexpected<std::string>{"max_file_bytes must be at least " + std::to_string(least)};
  }
  if (auto e = s->open_file()) {
    s->closed_ = true;
    return Unexpected<std::string>{*e};
  }
  s->io_ = std::thread{&ListModeSink::io_loop, s.get()};
  return s;
}

ListModeSink::~ListModeSink() {
  if (!closed_) {
    (void)close("");
  }
  if (fd_ >= 0) {
    (void)ops_->close(fd_);  // after a fault, or if open() failed half way: the .part file stays
  }
}

std::string ListModeSink::part_path(std::uint32_t segment) const {
  char num[16];
  (void)std::snprintf(num, sizeof num, "%04u", static_cast<unsigned>(segment));
  return cfg_.directory + "/" + cfg_.prefix + "-" + cfg_.run_name + "-" + num + ".mdql.part";
}

std::size_t ListModeSink::header_bytes_for(std::uint32_t segment) const {
  nlohmann::json m = cfg_.metadata;
  m["file"] = {{"segment", segment}, {"run_name", cfg_.run_name}};
  return listmode::encode_file_header(m.dump()).size();
}

// ---------------------------------------------------------------------------
// Encoder side: the pipeline's writer thread.

// [snippet:write]
void ListModeSink::write(std::span<const Coincidence> batch) {
  if (closed_) {
    return;
  }
  using Append = listmode::BlockWriter::Append;
  std::uint64_t written = 0;
  for (const auto& c : batch) {
    while (true) {
      const Append r = writer_.append(c);
      if (r == Append::ok) {
        ++written;
        if (writer_.records() == 1) {
          block_started_ = Clock::now();
        }
        break;
      }
      if (r == Append::invalid) {
        n_.invalid.fetch_add(1, std::memory_order_relaxed);
        break;
      }
      if (r == Append::time_reset) {
        n_.time_resets.fetch_add(1, std::memory_order_relaxed);
      }
      submit(false);  // full, out of time range or a reset: the record starts the next block
    }
  }
  n_.coincidences.fetch_add(written, std::memory_order_relaxed);
  n_.energies_clamped.store(writer_.energies_clamped(), std::memory_order_relaxed);
  // At a low rate a block fills slowly: hand it off anyway, so that a crash
  // loses at most max_block_delay of data that never left this process.
  if (writer_.records() > 0 && Clock::now() - block_started_ >= cfg_.max_block_delay) {
    submit(false);
  }
}
// [/snippet:write]

// [snippet:submit]
void ListModeSink::submit(bool end_of_run) {
  Item it;
  if (writer_.records() > 0) {
    const auto bytes = listmode::block_bytes(writer_.records());
    // Rotate if this block and the closing block would not fit. A new file
    // always has room: open() checked max_file_bytes against one full block.
    if (file_bytes_ + bytes + listmode::block_header_bytes > cfg_.max_file_bytes) {
      it.new_file_before = true;
      it.rotate_sequence = sequence_;
      ++encoder_segment_;
      sequence_ = 0;
      file_bytes_ = header_bytes_for(encoder_segment_);
    }
    it.buffer = current_;
    it.bytes = writer_.finish(sequence_++, 0);
    file_bytes_ += bytes;
  }
  it.end_of_run = end_of_run;
  it.final_sequence = sequence_;
  const bool need_buffer = it.buffer >= 0 && !end_of_run;
  std::unique_lock lock{mu_};
  full_.push_back(it);
  full_cv_.notify_one();
  if (!need_buffer) {
    return;
  }
  if (free_.empty()) {
    // Backpressure: the disk is behind. Wait; never drop.
    const auto t0 = Clock::now();
    free_cv_.wait(lock, [&] { return !free_.empty(); });
    n_.buffer_waits.fetch_add(1, std::memory_order_relaxed);
    n_.buffer_wait_ns.fetch_add(ns_since(t0), std::memory_order_relaxed);
  }
  current_ = free_.front();
  free_.pop_front();
  lock.unlock();
  writer_.reset(pool_[static_cast<std::size_t>(current_)]);
}
// [/snippet:submit]

std::optional<std::string> ListModeSink::close(std::string_view run_record) {
  if (closed_) {
    return close_result_;
  }
  closed_ = true;
  submit(true);
  io_.join();
  if (!faulted()) {
    write_run_record(run_record);  // the I/O thread has ended: this thread owns ops_ now
  }
  close_result_ = fault();
  return close_result_;
}

// [snippet:run_record]
void ListModeSink::write_run_record(std::string_view run_record) {
  nlohmann::json j;
  j["format"] = "MDQ-L1 run record";
  j["run_name"] = cfg_.run_name;
  j["files"] = nlohmann::json::array();
  for (const auto& f : files()) {
    j["files"].push_back(f.substr(f.find_last_of('/') + 1));
  }
  for (const auto& c : counters()) {
    j["sink_counters"][c.name] = c.value;
  }
  auto parsed = nlohmann::json::parse(run_record, nullptr, /*allow_exceptions=*/false);
  j["run"] = parsed.is_discarded() ? (run_record.empty() ? nlohmann::json(nullptr) : nlohmann::json(run_record))
                                   : std::move(parsed);
  // [/snippet:run_record]
  const std::string text = j.dump(2) + "\n";
  const std::string path = cfg_.directory + "/" + cfg_.prefix + "-" + cfg_.run_name + ".run.json";
  const std::string part = path + ".part";
  const auto fd = ops_->create(part);
  if (!fd) {
    return set_fault("create " + part + ": " + errno_message(fd.error()));
  }
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast): the text's bytes
  std::span<const std::byte> data{reinterpret_cast<const std::byte*>(text.data()), text.size()};
  while (!data.empty()) {
    const auto r = ops_->write(*fd, data);
    if (!r || *r == 0) {
      (void)ops_->close(*fd);
      return set_fault("write " + part + ": " + (r ? std::string{"wrote nothing"} : errno_message(r.error())));
    }
    data = data.subspan(*r);
  }
  int sync_error = 0;
  if (cfg_.fsync != FsyncPolicy::none) {
    sync_error = ops_->sync(*fd);
    n_.fsyncs.fetch_add(1, std::memory_order_relaxed);
  }
  if (const int e = ops_->close(*fd); sync_error != 0 || e != 0) {
    return set_fault((sync_error != 0 ? "fsync " : "close ") + part + ": " + errno_message(sync_error != 0 ? sync_error : e));
  }
  if (const int e = ops_->rename_no_replace(part, path); e != 0) {
    return set_fault("rename " + part + ": " + errno_message(e));
  }
  if (cfg_.fsync != FsyncPolicy::none) {
    if (const int e = ops_->sync_directory(cfg_.directory); e != 0) {
      set_fault("fsync " + cfg_.directory + ": " + errno_message(e));
    }
  }
}

// ---------------------------------------------------------------------------
// I/O side: the sink's own thread.

void ListModeSink::set_fault(std::string message) {
  const std::lock_guard lock{mu_};
  if (fault_.empty()) {
    fault_ = std::move(message);
  }
  faulted_.store(true, std::memory_order_release);
}

void ListModeSink::write_bytes(std::span<const std::byte> data) {
  while (!data.empty()) {
    const auto r = ops_->write(fd_, data);
    if (!r || *r == 0) {
      set_fault("write " + part_path(segment_) + ": " + (r ? std::string{"wrote nothing"} : errno_message(r.error())));
      return;
    }
    data = data.subspan(*r);  // a short write: write the rest
    n_.bytes.fetch_add(*r, std::memory_order_relaxed);
  }
}

std::optional<std::string> ListModeSink::open_file() {
  const auto path = part_path(segment_);
  const auto fd = ops_->create(path);
  if (!fd) {
    set_fault("create " + path + ": " + errno_message(fd.error()));
    return fault();
  }
  fd_ = *fd;
  nlohmann::json m = cfg_.metadata;
  m["file"] = {{"segment", segment_}, {"run_name", cfg_.run_name}};
  write_bytes(listmode::encode_file_header(m.dump()));
  blocks_since_sync_ = 0;
  return faulted() ? fault() : std::nullopt;
}

// [snippet:finish_file]
void ListModeSink::finish_file(std::uint32_t sequence, std::uint32_t flags) {
  listmode::BlockWriter closing{closing_, 1};
  write_bytes(std::span{closing_}.first(closing.finish(sequence, flags)));
  const auto part = part_path(segment_);
  const auto final_path = part.substr(0, part.size() - 5);  // without ".part"
  if (!faulted() && cfg_.fsync != FsyncPolicy::none) {
    const auto t0 = Clock::now();
    if (const int e = ops_->sync(fd_); e != 0) {
      set_fault("fsync " + part + ": " + errno_message(e));
    }
    n_.fsyncs.fetch_add(1, std::memory_order_relaxed);
    store_max(n_.max_fsync_ns, ns_since(t0));
  }
  if (const int e = ops_->close(fd_); e != 0) {
    set_fault("close " + part + ": " + errno_message(e));  // NFS reports write errors here
  }
  fd_ = -1;
  if (faulted()) {
    return;  // the .part name stays: the file is not known to be complete
  }
  if (const int e = ops_->rename_no_replace(part, final_path); e != 0) {
    set_fault("rename " + part + ": " + errno_message(e));
    return;
  }
  if (cfg_.fsync != FsyncPolicy::none) {
    if (const int e = ops_->sync_directory(cfg_.directory); e != 0) {
      set_fault("fsync " + cfg_.directory + ": " + errno_message(e));
      return;
    }
  }
  const std::lock_guard lock{mu_};
  files_.push_back(final_path);
  n_.files.fetch_add(1, std::memory_order_relaxed);
}
// [/snippet:finish_file]

// [snippet:io_loop]
void ListModeSink::io_loop() {
  while (true) {
    Item it;
    {
      std::unique_lock lock{mu_};
      full_cv_.wait(lock, [&] { return !full_.empty(); });
      it = full_.front();
      full_.pop_front();
    }
    if (it.new_file_before && !faulted()) {
      finish_file(it.rotate_sequence, listmode::block_flag_end_of_file);
      ++segment_;
      if (!faulted()) {
        (void)open_file();
      }
    }
    if (it.buffer >= 0) {
      if (!faulted()) {
        const auto t0 = Clock::now();
        write_bytes(std::span{pool_[static_cast<std::size_t>(it.buffer)]}.first(it.bytes));
        store_max(n_.max_write_ns, ns_since(t0));
        n_.blocks.fetch_add(1, std::memory_order_relaxed);
        if (cfg_.fsync == FsyncPolicy::interval && ++blocks_since_sync_ >= cfg_.fsync_every_blocks && !faulted()) {
          const auto t1 = Clock::now();
          if (const int e = ops_->sync(fd_); e != 0) {
            set_fault("fsync " + part_path(segment_) + ": " + errno_message(e));
          }
          n_.fsyncs.fetch_add(1, std::memory_order_relaxed);
          store_max(n_.max_fsync_ns, ns_since(t1));
          blocks_since_sync_ = 0;
        }
      } else {
        n_.blocks_dropped.fetch_add(1, std::memory_order_relaxed);
      }
      {
        const std::lock_guard lock{mu_};
        free_.push_back(it.buffer);
      }
      free_cv_.notify_one();
    }
    if (it.end_of_run) {
      if (!faulted()) {
        finish_file(it.final_sequence, listmode::block_flag_end_of_run);
      }
      return;
    }
  }
}
// [/snippet:io_loop]

// ---------------------------------------------------------------------------

std::optional<std::string> ListModeSink::fault() const {
  const std::lock_guard lock{mu_};
  return fault_.empty() ? std::nullopt : std::optional<std::string>{fault_};
}

std::string ListModeSink::describe() const {
  return "list-mode files " + cfg_.directory + "/" + cfg_.prefix + "-" + cfg_.run_name + "-NNNN.mdql (fsync " +
         std::string{to_string(cfg_.fsync)} + ", " + std::to_string(cfg_.buffers) + " blocks of " +
         std::to_string(cfg_.records_per_block) + " records)";
}

ListModeSinkStats ListModeSink::stats() const {
  auto g = [](const std::atomic<std::uint64_t>& a) { return a.load(std::memory_order_relaxed); };
  return ListModeSinkStats{g(n_.coincidences), g(n_.invalid),        g(n_.time_resets), g(n_.energies_clamped),
                           g(n_.blocks),       g(n_.bytes),          g(n_.files),       g(n_.buffer_waits),
                           g(n_.buffer_wait_ns), g(n_.fsyncs),       g(n_.max_fsync_ns), g(n_.max_write_ns),
                           g(n_.blocks_dropped)};
}

std::vector<DetectorCounter> ListModeSink::counters() const {
  const auto s = stats();
  return {{"coincidences", s.coincidences},     {"invalid", s.invalid},
          {"time_resets", s.time_resets},       {"energies_clamped", s.energies_clamped},
          {"blocks", s.blocks},                 {"bytes", s.bytes},
          {"files", s.files},                   {"buffer_waits", s.buffer_waits},
          {"buffer_wait_ns", s.buffer_wait_ns}, {"fsyncs", s.fsyncs},
          {"max_fsync_ns", s.max_fsync_ns},     {"max_write_ns", s.max_write_ns},
          {"blocks_dropped", s.blocks_dropped}};
}

std::vector<std::string> ListModeSink::files() const {
  const std::lock_guard lock{mu_};
  return files_;
}

// [snippet:factory]
std::unique_ptr<CoincidenceSinkPort> make_listmode_sink(const config::AcquisitionConfig& c, std::string& error) {
  const auto& o = c.output;
  ListModeSinkConfig s;
  s.directory = o.directory;
  s.prefix = o.prefix;
  // The run's UTC start time, to the millisecond, makes the name unique on one machine.
  const std::string now = utc_now_iso8601();
  for (const char ch : now) {
    if (ch != '-' && ch != ':' && ch != '.') {
      s.run_name += ch;
    }
  }
  s.max_file_bytes = o.max_file_mb << 20U;
  s.records_per_block = o.records_per_block;
  s.buffers = o.buffers;
  s.fsync = o.fsync == "none" ? FsyncPolicy::none : o.fsync == "interval" ? FsyncPolicy::interval : FsyncPolicy::close;
  s.fsync_every_blocks = o.fsync_every_blocks;
  s.max_block_delay = std::chrono::milliseconds{o.max_block_delay_ms};
  // What a reader needs to interpret the records without asking anyone: the
  // format, the software, the scanner, and the whole effective configuration.
  s.metadata = {
      {"format", "MDQ-L1"},
      {"software", std::string{"MiniDAQ "} + MINIDAQ_VERSION_STRING},
      {"created_utc", now},
      // Simulated data must never pass for measured data (Chapter 8). The
      // synthetic source is a simulation; a UDP source is taken to be a
      // detector, so a bench that feeds the link from a simulator says so in
      // the configuration's description (assumption: confirm with team how
      // NeuroLF marks test and phantom data).
      {"simulated", c.source.type != "udp"},
      {"scanner",
       {{"model", "MiniDAQ reference geometry (assumption: confirm with team)"},
        {"crystals_per_ring", ScannerGeometry::crystals_per_ring},
        {"crystal_rings", ScannerGeometry::crystal_rings},
        {"inner_radius_mm", ScannerGeometry::inner_radius_mm},
        {"axial_pitch_mm", ScannerGeometry::axial_pitch_mm},
        {"crystal_id", "ring * crystals_per_ring + transaxial"},
        {"crystal_angle", "(transaxial + 0.5) * 2 pi / crystals_per_ring"}}},
      {"records",
       {{"time_unit", "ps"},
        {"energy_lsb_kev", 1.0 / 32.0},
        {"delayed_window_ps", c.sorter.delay_ps},
        {"coincidence_window_ps", c.pipeline.coincidence_window_ps}}},
      {"configuration", config::to_json(c)},
  };
  auto sink = ListModeSink::open(std::move(s), make_posix_file_ops());
  if (!sink) {
    error = sink.error();
    return nullptr;
  }
  return std::move(*sink);
}
// [/snippet:factory]

}  // namespace minidaq::control
