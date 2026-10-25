// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <algorithm>
#include <cerrno>
#include <chrono>
#include <mutex>
#include <random>
#include <thread>
#include <vector>

#include "fast_sink.hpp"
#include "minidaq/format/list_mode.hpp"

using namespace minidaq;
using namespace std::chrono_literals;
using Clock = std::chrono::steady_clock;

namespace {

// A disk with a slow fsync (20 ms, as on a busy HDD or a network file system)
// and a fast write, that records when each byte was written and when it was
// made durable.
struct SlowDisk {
  std::mutex mu;
  std::vector<std::byte> data;
  std::vector<std::pair<std::size_t, Clock::time_point>> writes;  // end offset, time
  std::vector<std::pair<std::size_t, Clock::time_point>> syncs;   // bytes covered, time
  std::chrono::microseconds sync_time{20'000};
  std::size_t capacity = SIZE_MAX;
  bool closed = false;
};

class SlowOps final : public control::FileOps {
 public:
  explicit SlowOps(SlowDisk& d) : d_{d} {}
  Expected<int, int> create(const std::string&) override { return 3; }
  Expected<std::size_t, int> write(int, std::span<const std::byte> b) override {
    std::this_thread::sleep_for(20us);  // about 3 GB/s for a 64 KiB block: the disk itself is fast
    const std::lock_guard lock{d_.mu};
    if (d_.data.size() + b.size() > d_.capacity) {
      return Unexpected{ENOSPC};
    }
    d_.data.insert(d_.data.end(), b.begin(), b.end());
    d_.writes.emplace_back(d_.data.size(), Clock::now());
    return b.size();
  }
  int sync(int) override {
    std::this_thread::sleep_for(d_.sync_time);
    const std::lock_guard lock{d_.mu};
    d_.syncs.emplace_back(d_.data.size(), Clock::now());
    return 0;
  }
  int close(int) override {
    d_.closed = true;
    return 0;
  }
  int rename_no_replace(const std::string&, const std::string&) override { return 0; }
  int sync_directory(const std::string&) override { return 0; }

 private:
  SlowDisk& d_;
};

std::vector<Coincidence> stream(std::size_t n) {
  std::mt19937_64 rng{9};
  std::uniform_int_distribution<std::uint32_t> crystal(0, 18431);
  std::vector<Coincidence> v(n);
  for (std::size_t i = 0; i < n; ++i) {
    const auto t = static_cast<std::int64_t>(i) * 200'000;  // 5 M per second of data time
    v[i] = Coincidence{Single{Picoseconds{t}, CrystalId{crystal(rng)}, KeV{511.0F}},
                       Single{Picoseconds{t + 900}, CrystalId{crystal(rng)}, KeV{480.0F}}, CoincidenceKind::prompt};
  }
  return v;
}

std::vector<Coincidence> read_back(const std::vector<std::byte>& f, bool& end_of_run, std::size_t& issues) {
  listmode::Reader r{f};
  std::vector<Coincidence> out;
  listmode::BlockView b;
  while (r.next(b)) {
    for (std::size_t i = 0; i < b.record_count(); ++i) {
      out.push_back(listmode::decode_record(b, i).event);
    }
  }
  end_of_run = r.stats().end_of_run;
  issues = r.issues().size() + (r.header() ? 0 : 1);
  return out;
}

}  // namespace

// The time it takes this machine (and this build: Debug, sanitizers) just to
// encode the stream: what write() costs if the disk costs nothing.
Clock::duration encode_only(const std::vector<Coincidence>& in) {
  std::vector<std::byte> buf(listmode::block_bytes(4096));
  listmode::BlockWriter w{buf, 4096};
  const auto t0 = Clock::now();
  for (const auto& c : in) {
    if (w.append(c) != listmode::BlockWriter::Append::ok) {
      (void)w.finish(0, 0);
      w.reset();
      (void)w.append(c);
    }
  }
  return Clock::now() - t0;
}

TEST(FastSink, KeepsUpWithTheSorterAndLosesNothing) {
  SlowDisk disk;
  const auto in = stream(500'000);  // 123 blocks: a sink that fsyncs every block waits 2.5 s for the disk
  const auto baseline = encode_only(in);
  ex123::FastSink sink{std::make_unique<SlowOps>(disk), "/run.mdql"};
  Clock::duration in_write{0};
  int slow_calls = 0;
  for (std::size_t i = 0; i < in.size(); i += 4096) {
    const auto t0 = Clock::now();
    sink.write(std::span{in}.subspan(i, std::min<std::size_t>(4096, in.size() - i)));
    const auto dt = Clock::now() - t0;
    in_write += dt;
    slow_calls += dt >= disk.sync_time ? 1 : 0;
  }
  ASSERT_EQ(sink.close(""), std::nullopt);
  // What write() cost beyond encoding is time spent waiting for the disk.
  EXPECT_LT(in_write - baseline, 500ms) << "the writer thread must not pay for the disk's fsyncs";
  EXPECT_LE(slow_calls, 2) << "write() calls that took as long as an fsync (20 ms)";
  bool end = false;
  std::size_t issues = 0;
  EXPECT_EQ(read_back(disk.data, end, issues), in);
  EXPECT_EQ(issues, 0U);
  EXPECT_TRUE(end);
  EXPECT_TRUE(disk.closed);
}

TEST(FastSink, NoDataWaitsLongerThanMaxUnsyncedForAnFsync) {
  SlowDisk disk;
  const auto in = stream(300'000);
  ex123::FastSink sink{std::make_unique<SlowOps>(disk), "/run.mdql", ex123::Options{4096, 100ms, 32}};
  // A slow trickle, as at a low activity: 4096 coincidences every 10 ms.
  for (std::size_t i = 0; i < in.size(); i += 4096) {
    sink.write(std::span{in}.subspan(i, std::min<std::size_t>(4096, in.size() - i)));
    std::this_thread::sleep_for(10ms);
  }
  ASSERT_EQ(sink.close(""), std::nullopt);
  const std::lock_guard lock{disk.mu};
  ASSERT_FALSE(disk.syncs.empty());
  EXPECT_EQ(disk.syncs.back().first, disk.data.size()) << "close() makes everything durable";
  EXPECT_LT(disk.syncs.size(), disk.writes.size() / 3) << "one fsync per block is the slow design";
  // Every write is covered by an fsync that started within max_unsynced (plus
  // scheduling slack) and ended one sync_time later.
  for (const auto& [end, when] : disk.writes) {
    const auto covering = std::find_if(disk.syncs.begin(), disk.syncs.end(), [&](const auto& s) { return s.first >= end; });
    ASSERT_NE(covering, disk.syncs.end());
    EXPECT_LT(covering->second - when, 100ms + disk.sync_time + 50ms) << "bytes up to " << end;
  }
}

TEST(FastSink, AFullDiskIsAFaultAndDoesNotHang) {
  SlowDisk disk;
  disk.capacity = 200'000;
  disk.sync_time = 1ms;
  const auto in = stream(200'000);
  ex123::FastSink sink{std::make_unique<SlowOps>(disk), "/run.mdql", ex123::Options{4096, 100ms, 4}};
  for (std::size_t i = 0; i < in.size(); i += 4096) {
    sink.write(std::span{in}.subspan(i, std::min<std::size_t>(4096, in.size() - i)));
  }
  const auto r = sink.close("");
  ASSERT_TRUE(r);
  EXPECT_NE(r->find("No space left on device"), std::string::npos) << *r;
  EXPECT_EQ(sink.fault(), r);
}
