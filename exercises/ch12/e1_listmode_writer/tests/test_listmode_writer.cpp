// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <random>
#include <vector>

#include "listmode_writer.hpp"
#include "minidaq/core/byte_io.hpp"
#include "minidaq/core/crc32.hpp"
#include "minidaq/format/list_mode.hpp"

using namespace minidaq;

namespace {

// 2,000 coincidences over about 20 ms: blocks must end on the 32-bit time
// offset (4.29 ms) as well as on the record count.
std::vector<Coincidence> stream(std::size_t n = 2000, std::uint64_t seed = 1) {
  std::mt19937_64 rng{seed};
  std::uniform_int_distribution<std::uint32_t> crystal(0, 18431);
  std::uniform_int_distribution<std::int64_t> gap(0, 20'000'000);
  std::uniform_int_distribution<int> e(435 * 32, 585 * 32);
  std::vector<Coincidence> v;
  std::int64_t t = 5'000'000'000;
  for (std::size_t i = 0; i < n; ++i) {
    t += gap(rng);
    const bool delayed = i % 9 == 4;
    v.push_back(Coincidence{
        Single{Picoseconds{t}, CrystalId{crystal(rng)}, KeV{static_cast<float>(e(rng)) / 32.0F}},
        Single{Picoseconds{t + (delayed ? 100'500 : 700)}, CrystalId{crystal(rng)}, KeV{static_cast<float>(e(rng)) / 32.0F}},
        delayed ? CoincidenceKind::delayed : CoincidenceKind::prompt});
  }
  return v;
}

std::vector<Coincidence> read_with_minidaq(listmode::Reader& r) {
  std::vector<Coincidence> out;
  listmode::BlockView b;
  while (r.next(b)) {
    for (std::size_t i = 0; i < b.record_count(); ++i) {
      out.push_back(listmode::decode_record(b, i).event);
    }
  }
  return out;
}

}  // namespace

TEST(ListModeWriter, RoundTrip) {
  const auto in = stream();
  const auto f = ex121::write_file(R"({"run":"t"})", in, 256);
  const auto r = ex121::read_file(f);
  ASSERT_TRUE(r.header_ok);
  EXPECT_EQ(r.metadata, R"({"run":"t"})");
  EXPECT_TRUE(r.bad_blocks.empty());
  EXPECT_FALSE(r.damaged_header);
  EXPECT_TRUE(r.end_of_run);
  EXPECT_EQ(r.events, in) << "energies are multiples of 1/32 keV here, so every field survives exactly";
}

TEST(ListModeWriter, MiniDaqReadsYourFile) {
  const auto in = stream();
  const auto f = ex121::write_file("{}", in, 256);
  listmode::Reader r{f};
  ASSERT_TRUE(r.header());
  const auto out = read_with_minidaq(r);
  for (const auto& i : r.issues()) {
    ADD_FAILURE() << "at byte " << i.offset << ": " << listmode::to_string(i.error);
  }
  EXPECT_EQ(out, in);
  EXPECT_TRUE(r.stats().end_of_run);
  EXPECT_GT(r.stats().blocks, 8U) << "2000 records in 256-record blocks, and blocks that end on the time offset";
}

TEST(ListModeWriter, YouReadMiniDaqsFile) {
  const auto in = stream(1000, 2);
  std::vector<std::byte> f = listmode::encode_file_header(R"({"x":1})");
  std::vector<std::byte> buf(listmode::block_bytes(100));
  listmode::BlockWriter w{buf, 100};
  std::uint32_t seq = 0;
  auto emit = [&](std::uint32_t flags) {
    const auto n = w.finish(seq++, flags);
    f.insert(f.end(), buf.begin(), buf.begin() + static_cast<std::ptrdiff_t>(n));
    w.reset();
  };
  for (const auto& c : in) {
    if (w.append(c) != listmode::BlockWriter::Append::ok) {
      emit(0);
      ASSERT_EQ(w.append(c), listmode::BlockWriter::Append::ok);
    }
  }
  const listmode::Tag tag{2, in.back().first.time, 5};
  if (w.append(tag) != listmode::BlockWriter::Append::ok) {
    emit(0);
    ASSERT_EQ(w.append(tag), listmode::BlockWriter::Append::ok);
  }
  emit(listmode::block_flag_end_of_run);
  const auto r = ex121::read_file(f);
  ASSERT_TRUE(r.header_ok);
  EXPECT_EQ(r.events, in) << "and the tag at the end is not a coincidence";
  EXPECT_TRUE(r.end_of_run);
}

TEST(ListModeWriter, EveryCorruptPayloadByteIsDetected) {
  const auto in = stream(600, 3);
  const auto good = ex121::write_file("{}", in, 100);
  // Find the blocks with MiniDAQ's reader.
  listmode::Reader probe{good};
  std::vector<listmode::BlockView> blocks;
  listmode::BlockView b;
  while (probe.next(b)) {
    blocks.push_back(b);
  }
  ASSERT_GE(blocks.size(), 7U);
  std::mt19937_64 rng{4};
  for (const auto& blk : blocks) {
    if (blk.record_count() == 0) {
      continue;
    }
    for (int trial = 0; trial < 20; ++trial) {
      auto bad = good;
      const auto at = blk.offset + listmode::block_header_bytes +
                      std::uniform_int_distribution<std::size_t>{0, blk.records.size() - 1}(rng);
      bad[at] ^= static_cast<std::byte>(1U << (trial % 8));
      const auto r = ex121::read_file(bad);
      ASSERT_EQ(r.bad_blocks, std::vector<std::size_t>{blk.offset}) << "byte " << at;
      // Everything else is still there, and nothing from the damaged block.
      EXPECT_EQ(r.events.size(), in.size() - blk.record_count()) << "byte " << at;
      for (const auto& c : r.events) {
        ASSERT_NE(std::find(in.begin(), in.end(), c), in.end()) << "byte " << at << ": a record that was never written";
      }
    }
  }
}

TEST(ListModeWriter, VersionsAndADamagedHeader) {
  const auto f = ex121::write_file(R"({"a":1})", stream(10), 100);
  auto reseal = [](std::vector<std::byte> h) {
    const std::size_t at = minidaq::load_le<std::uint32_t>(h, 12) - 8;
    minidaq::store_le<std::uint32_t>(h, at, minidaq::crc32(std::span<const std::byte>{h}.first(at)));
    return h;
  };
  auto minor = f;
  minidaq::store_le<std::uint16_t>(minor, 10, 7);
  const auto r7 = ex121::read_file(reseal(minor));
  EXPECT_TRUE(r7.header_ok) << "a 1.0 reader reads a 1.7 file: minor versions only add";
  EXPECT_EQ(r7.minor, 7);
  EXPECT_EQ(r7.events.size(), 10U);
  auto major = f;
  minidaq::store_le<std::uint16_t>(major, 8, 2);
  EXPECT_FALSE(ex121::read_file(reseal(major)).header_ok) << "a 2.0 file may mean anything";
  auto flipped = f;
  flipped[33] ^= std::byte{1};  // in the metadata
  EXPECT_FALSE(ex121::read_file(flipped).header_ok);
}
