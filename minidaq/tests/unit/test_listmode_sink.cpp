// SPDX-License-Identifier: MIT
// The list-mode sink with file operations that can be made to fail: a full
// disk, short writes, a slow disk. And once with the real file system.
#include <gtest/gtest.h>

#include <algorithm>
#include <cerrno>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <map>
#include <mutex>
#include <random>
#include <string>
#include <thread>

#include <unistd.h>
#include <vector>

#include <nlohmann/json.hpp>

#include "minidaq/control/acquisition_service.hpp"
#include "minidaq/control/adapters.hpp"
#include "minidaq/control/listmode_sink.hpp"
#include "minidaq/format/list_mode.hpp"
#include "eventually.hpp"

using namespace minidaq;
using namespace minidaq::control;
using namespace std::chrono_literals;

namespace {

// An in-memory file system that records every call, for the ordering checks,
// and fails on demand.
struct Disk {
  std::mutex mu;
  std::map<std::string, std::vector<std::byte>> files;
  std::map<int, std::string> open;
  std::vector<std::string> log;  // "create a", "sync a", "close a", "rename a b", "syncdir d"
  int next_fd = 3;
  std::size_t capacity = SIZE_MAX;   // bytes, all files together: ENOSPC beyond
  std::size_t max_write = SIZE_MAX;  // a short write returns at most this many bytes
  std::chrono::microseconds write_delay{0};
  std::size_t used = 0;
};

class FakeOps final : public FileOps {
 public:
  explicit FakeOps(Disk& d) : d_{d} {}
  Expected<int, int> create(const std::string& path) override {
    const std::lock_guard lock{d_.mu};
    if (d_.files.count(path) != 0) {
      return Unexpected{EEXIST};
    }
    d_.files[path];
    d_.open[d_.next_fd] = path;
    d_.log.push_back("create " + path);
    return d_.next_fd++;
  }
  Expected<std::size_t, int> write(int fd, std::span<const std::byte> data) override {
    if (d_.write_delay.count() > 0) {
      std::this_thread::sleep_for(d_.write_delay);  // sleep: device (a slow disk)
    }
    const std::lock_guard lock{d_.mu};
    if (d_.used >= d_.capacity) {
      return Unexpected{ENOSPC};
    }
    const std::size_t n = std::min({data.size(), d_.max_write, d_.capacity - d_.used});
    auto& f = d_.files[d_.open.at(fd)];
    f.insert(f.end(), data.begin(), data.begin() + static_cast<std::ptrdiff_t>(n));
    d_.used += n;
    return n;
  }
  int sync(int fd) override { return note("sync " + d_.open.at(fd)); }
  int close(int fd) override {
    const std::lock_guard lock{d_.mu};
    d_.log.push_back("close " + d_.open.at(fd));
    d_.open.erase(fd);
    return 0;
  }
  int rename_no_replace(const std::string& from, const std::string& to) override {
    const std::lock_guard lock{d_.mu};
    if (d_.files.count(to) != 0) {
      return EEXIST;
    }
    d_.files[to] = std::move(d_.files.at(from));
    d_.files.erase(from);
    d_.log.push_back("rename " + from + " " + to);
    return 0;
  }
  int sync_directory(const std::string& dir) override { return note("syncdir " + dir); }

 private:
  int note(std::string s) {
    const std::lock_guard lock{d_.mu};
    d_.log.push_back(std::move(s));
    return 0;
  }
  Disk& d_;
};

ListModeSinkConfig small_config() {
  ListModeSinkConfig c;
  c.directory = "/d";
  c.prefix = "t";
  c.run_name = "run1";
  c.metadata = {{"format", "MDQ-L1"}};
  c.records_per_block = 64;
  c.buffers = 4;
  return c;
}

std::vector<Coincidence> stream(std::size_t n, std::uint64_t seed = 1) {
  std::mt19937_64 rng{seed};
  std::uniform_int_distribution<std::uint32_t> crystal(0, 18431);
  std::uniform_int_distribution<std::int64_t> gap(0, 200'000);
  std::vector<Coincidence> v;
  std::int64_t t = 0;
  for (std::size_t i = 0; i < n; ++i) {
    t += gap(rng);
    v.push_back(Coincidence{Single{Picoseconds{t}, CrystalId{crystal(rng)}, KeV{511.0F}},
                            Single{Picoseconds{t + 1000}, CrystalId{crystal(rng)}, KeV{450.0F}},
                            i % 5 == 0 ? CoincidenceKind::delayed : CoincidenceKind::prompt});
  }
  return v;
}

void write_in_batches(ListModeSink& s, const std::vector<Coincidence>& v, std::size_t batch = 100) {
  for (std::size_t i = 0; i < v.size(); i += batch) {
    s.write(std::span{v}.subspan(i, std::min(batch, v.size() - i)));
  }
}

struct ReadBack {
  std::vector<Coincidence> events;
  listmode::ReaderStats stats;
  std::size_t issues = 0;
  std::string metadata;
};

ReadBack read_file(std::span<const std::byte> bytes) {
  listmode::Reader r{bytes};
  ReadBack out;
  if (!r.header()) {
    out.issues = 1;
    return out;
  }
  out.metadata = std::string{r.header()->metadata};
  listmode::BlockView b;
  while (r.next(b)) {
    for (std::size_t i = 0; i < b.record_count(); ++i) {
      out.events.push_back(listmode::decode_record(b, i).event);
    }
  }
  out.stats = r.stats();
  out.issues = r.issues().size();
  return out;
}

std::size_t index_of(const std::vector<std::string>& log, const std::string& entry) {
  return static_cast<std::size_t>(std::find(log.begin(), log.end(), entry) - log.begin());
}

}  // namespace

TEST(ListModeSink, WritesEveryCoincidenceAndClosesTheRun) {
  // REQ: SRS-OUT-001
  Disk disk;
  auto s = ListModeSink::open(small_config(), std::make_unique<FakeOps>(disk));
  ASSERT_TRUE(s) << s.error();
  const auto in = stream(10'000);
  write_in_batches(**s, in);
  EXPECT_EQ((*s)->close(""), std::nullopt);
  ASSERT_EQ((*s)->files(), std::vector<std::string>{"/d/t-run1-0000.mdql"});
  EXPECT_EQ(disk.files.count("/d/t-run1-0000.mdql.part"), 0U);
  const auto back = read_file(disk.files.at("/d/t-run1-0000.mdql"));
  EXPECT_EQ(back.issues, 0U);
  EXPECT_TRUE(back.stats.end_of_run);
  ASSERT_EQ(back.events, in) << "times, crystals, kinds and these energies survive exactly";
  const auto st = (*s)->stats();
  EXPECT_EQ(st.coincidences, in.size());
  EXPECT_EQ(st.blocks, (in.size() + 63) / 64);
  EXPECT_EQ(st.files, 1U);
  EXPECT_EQ(st.bytes, disk.files.at("/d/t-run1-0000.mdql").size());
  const auto meta = nlohmann::json::parse(back.metadata);
  EXPECT_EQ(meta["format"], "MDQ-L1");
  EXPECT_EQ(meta["file"]["segment"], 0);
  EXPECT_EQ((*s)->close(""), std::nullopt) << "a second close changes nothing";
}

TEST(ListModeSink, RotatesFilesAndEndsEachWithAClosingBlock) {
  // REQ: SRS-OUT-002
  Disk disk;
  auto cfg = small_config();
  cfg.max_file_bytes = 20'000;
  auto s = ListModeSink::open(cfg, std::make_unique<FakeOps>(disk));
  ASSERT_TRUE(s) << s.error();
  const auto in = stream(10'000);
  write_in_batches(**s, in, 333);
  ASSERT_EQ((*s)->close(""), std::nullopt);
  const auto files = (*s)->files();
  ASSERT_GT(files.size(), 5U);
  std::vector<Coincidence> all;
  for (std::size_t k = 0; k < files.size(); ++k) {
    const auto& bytes = disk.files.at(files[k]);
    EXPECT_LE(bytes.size(), cfg.max_file_bytes) << files[k];
    const auto back = read_file(bytes);
    EXPECT_EQ(back.issues, 0U) << files[k] << ": every file's sequence numbers start at 0";
    EXPECT_TRUE(back.stats.end_of_file) << files[k];
    EXPECT_EQ(back.stats.end_of_run, k + 1 == files.size()) << files[k];
    EXPECT_EQ(nlohmann::json::parse(back.metadata)["file"]["segment"], k);
    all.insert(all.end(), back.events.begin(), back.events.end());
  }
  EXPECT_EQ(all, in) << "nothing lost or repeated at the file boundaries";
}

TEST(ListModeSink, MakesEachFileDurableBeforeItsFinalName) {
  // REQ: SRS-OUT-003
  for (const auto policy : {FsyncPolicy::none, FsyncPolicy::close, FsyncPolicy::interval}) {
    Disk disk;
    auto cfg = small_config();
    cfg.fsync = policy;
    cfg.fsync_every_blocks = 10;
    cfg.max_file_bytes = 40'000;
    auto s = ListModeSink::open(cfg, std::make_unique<FakeOps>(disk));
    ASSERT_TRUE(s) << s.error();
    write_in_batches(**s, stream(5'000));
    ASSERT_EQ((*s)->close(""), std::nullopt);
    const auto& log = disk.log;
    for (const auto& f : (*s)->files()) {
      const auto part = f + ".part";
      SCOPED_TRACE(f);
      const auto renamed = index_of(log, "rename " + part + " " + f);
      ASSERT_LT(renamed, log.size());
      EXPECT_LT(index_of(log, "close " + part), renamed);
      if (policy == FsyncPolicy::none) {
        EXPECT_EQ(index_of(log, "sync " + part), log.size());
        continue;
      }
      // Data on disk, then the name, then the name on disk.
      EXPECT_LT(index_of(log, "sync " + part), index_of(log, "close " + part));
      EXPECT_LT(renamed, static_cast<std::size_t>(std::find(log.begin() + static_cast<std::ptrdiff_t>(renamed),
                                                            log.end(), "syncdir /d") -
                                                  log.begin()));
    }
    const auto syncs = static_cast<std::uint64_t>(std::count_if(log.begin(), log.end(), [](const std::string& e) {
      return e.rfind("sync /", 0) == 0 && e.ends_with(".mdql.part");
    }));
    EXPECT_EQ((*s)->stats().fsyncs, syncs + (policy == FsyncPolicy::none ? 0 : 1)) << "and one for the run record";
    const auto blocks = (*s)->stats().blocks;
    const auto files = (*s)->files().size();
    if (policy == FsyncPolicy::close) {
      EXPECT_EQ(syncs, files);
    } else if (policy == FsyncPolicy::interval) {
      // One per file, plus one per 10 blocks within each file (the count restarts in a new file).
      EXPECT_GT(syncs, files);
      EXPECT_LE(syncs, files + blocks / 10);
      EXPECT_GE(syncs, files + (blocks - 9 * files) / 10);
    }
  }
}

TEST(ListModeSink, ShortWritesAreCompleted) {
  // REQ: SRS-OUT-004
  Disk disk;
  disk.max_write = 7;
  auto s = ListModeSink::open(small_config(), std::make_unique<FakeOps>(disk));
  ASSERT_TRUE(s) << s.error();
  const auto in = stream(2'000);
  write_in_batches(**s, in);
  ASSERT_EQ((*s)->close(""), std::nullopt);
  EXPECT_EQ(read_file(disk.files.at("/d/t-run1-0000.mdql")).events, in);
}

TEST(ListModeSink, AFullDiskIsAFaultAndTheFileStaysPart) {
  // REQ: SRS-OUT-005
  Disk disk;
  disk.capacity = 30'000;
  auto s = ListModeSink::open(small_config(), std::make_unique<FakeOps>(disk));
  ASSERT_TRUE(s) << s.error();
  const auto in = stream(10'000);
  write_in_batches(**s, in);  // must not hang: after the fault, buffers still come back
  const auto r = (*s)->close("");
  ASSERT_TRUE(r);
  EXPECT_NE(r->find("No space left on device"), std::string::npos) << *r;
  EXPECT_EQ((*s)->fault(), r);
  EXPECT_TRUE((*s)->files().empty());
  ASSERT_EQ(disk.files.count("/d/t-run1-0000.mdql.part"), 1U) << "not renamed: not known to be complete";
  // What did reach the disk is readable up to the last complete block.
  const auto back = read_file(disk.files.at("/d/t-run1-0000.mdql.part"));
  EXPECT_GT(back.events.size(), 1'000U);
  EXPECT_FALSE(back.stats.end_of_file);
  EXPECT_TRUE(std::equal(back.events.begin(), back.events.end(), in.begin())) << "a prefix of the input";
  const auto st = (*s)->stats();
  EXPECT_GT(st.blocks_dropped, 0U);
  EXPECT_EQ(st.blocks + st.blocks_dropped, (in.size() + 63) / 64);
}

TEST(ListModeSink, ASlowDiskSlowsTheWriterDownInsteadOfLosingData) {
  // REQ: SRS-OUT-006
  Disk disk;
  disk.write_delay = 2ms;
  auto cfg = small_config();
  cfg.buffers = 2;
  auto s = ListModeSink::open(cfg, std::make_unique<FakeOps>(disk));
  ASSERT_TRUE(s) << s.error();
  const auto in = stream(3'000);
  write_in_batches(**s, in, 500);
  ASSERT_EQ((*s)->close(""), std::nullopt);
  const auto st = (*s)->stats();
  EXPECT_GT(st.buffer_waits, 0U);
  EXPECT_GT(st.buffer_wait_ns, 10'000'000U) << "about 2 ms per block, 47 blocks";
  EXPECT_EQ(read_file(disk.files.at("/d/t-run1-0000.mdql")).events, in);
}

TEST(ListModeSink, ABlockIsWrittenAtTheLatestAfterTheMaximumDelay) {
  // REQ: SRS-OUT-007
  Disk disk;
  auto cfg = small_config();
  cfg.max_block_delay = 20ms;
  auto s = ListModeSink::open(cfg, std::make_unique<FakeOps>(disk));
  ASSERT_TRUE(s) << s.error();
  const auto in = stream(10);  // far fewer than a block
  (*s)->write(in);
  EXPECT_EQ((*s)->stats().blocks, 0U);
  std::this_thread::sleep_for(30ms);  // sleep: minimum (more than max_block_delay)
  (*s)->write({});  // the pipeline's writer calls write() at least every max_batch_delay
  const auto deadline = std::chrono::steady_clock::now() + 2s;
  while ((*s)->stats().blocks == 0 && std::chrono::steady_clock::now() < deadline) {
    std::this_thread::sleep_for(1ms);  // sleep: poll
  }
  EXPECT_EQ((*s)->stats().blocks, 1U);
  std::vector<std::byte> on_disk;
  {
    const std::lock_guard lock{disk.mu};
    on_disk = disk.files.at("/d/t-run1-0000.mdql.part");
  }
  EXPECT_EQ(read_file(on_disk).events, in) << "before close, the records are in the file";
  ASSERT_EQ((*s)->close(""), std::nullopt);
}

TEST(ListModeSink, RejectsBadConfigurationsAndExistingFiles) {
  // REQ: SRS-OUT-008
  Disk disk;
  auto bad = small_config();
  bad.run_name = "";
  EXPECT_FALSE(ListModeSink::open(bad, std::make_unique<FakeOps>(disk)));
  bad = small_config();
  bad.max_file_bytes = 1000;  // smaller than one 64-record block
  const auto r = ListModeSink::open(bad, std::make_unique<FakeOps>(disk));
  ASSERT_FALSE(r);
  EXPECT_NE(r.error().find("max_file_bytes"), std::string::npos);
  disk.files["/d/t-run1-0000.mdql.part"] = {};
  const auto exists = ListModeSink::open(small_config(), std::make_unique<FakeOps>(disk));
  ASSERT_FALSE(exists);
  EXPECT_NE(exists.error().find("File exists"), std::string::npos) << exists.error();
}

TEST(ListModeSink, WritesRealFilesThroughTheService) {
  // REQ: SRS-OUT-009, SRS-OUT-011, SRS-OUT-012
  const auto dir = std::filesystem::temp_directory_path() / ("minidaq-lm-" + std::to_string(::getpid()));
  std::filesystem::remove_all(dir);
  std::filesystem::create_directories(dir);
  AcquisitionService svc{with_default_adapters()};
  config::AcquisitionConfig c;
  c.source.rate_hz = 2e6;
  c.stop_after_s = 0.1;
  c.output.type = "listmode";
  c.output.directory = dir.string();
  c.output.max_file_mb = 1;
  ASSERT_TRUE(svc.configure(c, "test").ok);
  ASSERT_TRUE(svc.start("test").ok);
  ASSERT_TRUE(svc.wait_for(AcqState::configured, test_support::patience)) << svc.status().dump();
  const auto st = svc.status();
  EXPECT_TRUE(st["fault"].is_null()) << st["fault"];
  const auto written = st["sink_counters"]["coincidences"].get<std::uint64_t>();
  EXPECT_EQ(written, st["stages"][4]["in"].get<std::uint64_t>()) << "the sink got everything the writer did";
  std::uint64_t read = 0;
  int files = 0;
  nlohmann::json record;
  for (const auto& e : std::filesystem::directory_iterator{dir}) {
    if (e.path().string().ends_with(".run.json")) {
      std::ifstream in{e.path()};
      record = nlohmann::json::parse(in);
      continue;
    }
    ASSERT_EQ(e.path().extension(), ".mdql") << e.path() << ": no .part file after a clean run";
    std::ifstream in{e.path(), std::ios::binary};
    const std::vector<char> raw{std::istreambuf_iterator<char>{in}, std::istreambuf_iterator<char>{}};
    const auto back = read_file(std::as_bytes(std::span{raw}));
    EXPECT_EQ(back.issues, 0U);
    read += back.events.size();
    ++files;
    const auto meta = nlohmann::json::parse(back.metadata);
    EXPECT_EQ(meta["configuration"]["output"]["type"], "listmode");
    EXPECT_EQ(meta["simulated"], true) << "the synthetic source is a simulation";
    EXPECT_TRUE(meta["configuration"]["sorter"].contains("multiples")) << "defaults are stored too";
  }
  // The run record: the service's counters, next to the data (SRS-OUT-010).
  ASSERT_TRUE(record.is_object()) << "no run record";
  EXPECT_EQ(record["files"].size(), static_cast<std::size_t>(files));
  EXPECT_EQ(record["sink_counters"]["coincidences"].get<std::uint64_t>(), written);
  EXPECT_TRUE(record["run"]["detector_counters"].is_object()) << record.dump();
  EXPECT_EQ(record["run"]["stages"][4]["in"], st["stages"][4]["in"]);
  EXPECT_EQ(record["run"]["integrity"]["complete"], true) << record["run"]["integrity"];
  EXPECT_GT(written, 0U);
  EXPECT_EQ(read, written);
  EXPECT_EQ(static_cast<std::uint64_t>(files), st["sink_counters"]["files"].get<std::uint64_t>());
  std::filesystem::remove_all(dir);
}

TEST(ListModeSink, StoresTheRunRecordNextToTheFiles) {
  // REQ: SRS-OUT-010
  Disk disk;
  auto cfg = small_config();
  cfg.max_file_bytes = 20'000;
  auto s = ListModeSink::open(cfg, std::make_unique<FakeOps>(disk));
  ASSERT_TRUE(s) << s.error();
  write_in_batches(**s, stream(3'000));
  ASSERT_EQ((*s)->close(R"({"detector_counters": {"packets_lost": 3}})"), std::nullopt);
  const std::string path = "/d/t-run1.run.json";
  ASSERT_EQ(disk.files.count(path), 1U);
  const auto& raw = disk.files.at(path);
  const auto j = nlohmann::json::parse(std::string{reinterpret_cast<const char*>(raw.data()), raw.size()});
  EXPECT_EQ(j["format"], "MDQ-L1 run record");
  EXPECT_EQ(j["run_name"], "run1");
  EXPECT_EQ(j["run"]["detector_counters"]["packets_lost"], 3) << "the caller's record, as JSON";
  EXPECT_EQ(j["sink_counters"]["coincidences"], 3000);
  ASSERT_EQ(j["files"].size(), (*s)->files().size());
  EXPECT_EQ(j["files"][0], "t-run1-0000.mdql") << "names relative to the directory";
  // Written after the last segment is complete, and durable like one.
  const auto& log = disk.log;
  const auto renamed = index_of(log, "rename " + path + ".part " + path);
  ASSERT_LT(renamed, log.size());
  EXPECT_LT(index_of(log, "rename " + (*s)->files().back() + ".part " + (*s)->files().back()),
            index_of(log, "create " + path + ".part"));
  EXPECT_LT(index_of(log, "sync " + path + ".part"), renamed);
  EXPECT_EQ(log.back(), "syncdir /d");

  Disk disk2;
  auto s2 = ListModeSink::open(small_config(), std::make_unique<FakeOps>(disk2));
  ASSERT_TRUE(s2) << s2.error();
  ASSERT_EQ((*s2)->close("not json"), std::nullopt);
  const auto& raw2 = disk2.files.at(path);
  const auto j2 = nlohmann::json::parse(std::string{reinterpret_cast<const char*>(raw2.data()), raw2.size()});
  EXPECT_EQ(j2["run"], "not json") << "kept as text, not dropped";
}
