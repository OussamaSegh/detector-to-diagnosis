// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <cstddef>
#include <cstdint>
#include <fstream>
#include <iterator>
#include <random>
#include <string>
#include <vector>

#include "minidaq/core/byte_io.hpp"
#include "minidaq/core/crc32.hpp"
#include "minidaq/format/list_mode.hpp"

using namespace minidaq;
using namespace minidaq::listmode;

namespace {

Coincidence pair(std::int64_t t, std::uint32_t a, std::uint32_t b, std::int64_t dt, float ea = 511.0F,
                 float eb = 480.0F, CoincidenceKind kind = CoincidenceKind::prompt) {
  return Coincidence{Single{Picoseconds{t}, CrystalId{a}, KeV{ea}}, Single{Picoseconds{t + dt}, CrystalId{b}, KeV{eb}},
                     kind};
}

// A whole file: header, then the coincidences in blocks of at most
// max_records, the last block flagged end of run.
struct File {
  std::vector<std::byte> bytes;
  std::vector<std::size_t> block_offsets;
};

File write_file(const std::vector<Coincidence>& events, std::size_t max_records, std::string_view meta = "{}") {
  File f;
  f.bytes = encode_file_header(meta);
  std::vector<std::byte> buf(block_bytes(max_records));
  std::uint32_t seq = 0;
  BlockWriter w{buf, seq, max_records};
  auto emit = [&](bool last) {
    const auto n = w.finish(last);
    f.block_offsets.push_back(f.bytes.size());
    f.bytes.insert(f.bytes.end(), buf.begin(), buf.begin() + static_cast<std::ptrdiff_t>(n));
    w = BlockWriter{buf, ++seq, max_records};
  };
  for (const auto& c : events) {
    if (w.append(c) != BlockWriter::Append::ok) {
      emit(false);
      EXPECT_EQ(w.append(c), BlockWriter::Append::ok);
    }
  }
  emit(true);
  return f;
}

std::vector<Coincidence> read_all(std::span<const std::byte> file, Reader* out_reader = nullptr) {
  Reader r{file};
  std::vector<Coincidence> out;
  BlockView b;
  while (r.next(b)) {
    for (std::size_t i = 0; i < b.record_count(); ++i) {
      const auto rec = decode_record(b, i);
      EXPECT_FALSE(rec.is_tag);
      out.push_back(rec.event);
    }
  }
  if (out_reader != nullptr) {
    *out_reader = r;
  }
  return out;
}

std::vector<Coincidence> stream(std::size_t n, std::uint64_t seed) {
  std::mt19937_64 rng{seed};
  std::uniform_int_distribution<std::uint32_t> crystal(0, 18431);
  std::uniform_int_distribution<std::int64_t> gap(0, 20'000'000);  // up to 20 us between coincidences
  std::uniform_int_distribution<std::int64_t> dt(0, 4000);
  std::uniform_int_distribution<int> energy(435 * 32, 585 * 32);
  std::vector<Coincidence> v;
  std::int64_t t = 1'000'000'000;
  for (std::size_t i = 0; i < n; ++i) {
    t += gap(rng);
    const bool delayed = i % 7 == 3;
    v.push_back(pair(t, crystal(rng), crystal(rng), dt(rng) + (delayed ? 100'000 : 0),
                     static_cast<float>(energy(rng)) / 32.0F, static_cast<float>(energy(rng)) / 32.0F,
                     delayed ? CoincidenceKind::delayed : CoincidenceKind::prompt));
  }
  return v;
}

}  // namespace

TEST(ListMode, FileHeaderRoundTrip) {
  // REQ: SRS-LMF-003
  const std::string meta = R"({"format":"MDQ-L1","run":"r42"})";
  const auto h = encode_file_header(meta);
  EXPECT_EQ(h.size() % 8, 0U);
  EXPECT_EQ(h.size(), 32U + 32U + 8U);  // 31 bytes of metadata padded to 32
  const auto p = parse_file_header(h);
  ASSERT_TRUE(p);
  EXPECT_EQ(p->metadata, meta);
  EXPECT_EQ(p->header_bytes, h.size());
  EXPECT_EQ(p->major, 1);
  EXPECT_EQ(p->minor, 0);
  EXPECT_TRUE(parse_file_header(encode_file_header("")));
  EXPECT_TRUE(encode_file_header(std::string(max_metadata_bytes + 1, ' ')).empty());
}

TEST(ListMode, FileHeaderRejectsDamageAndUnknownVersions) {
  // REQ: SRS-LMF-003
  const auto good = encode_file_header(R"({"a":1})");
  for (std::size_t i = 0; i < good.size(); ++i) {
    auto h = good;
    h[i] ^= std::byte{0x10};
    EXPECT_FALSE(parse_file_header(h)) << "byte " << i;
  }
  auto reseal = [](std::vector<std::byte> h) {
    store_le<std::uint32_t>(h, h.size() - 8, crc32(std::span<const std::byte>{h}.first(h.size() - 8)));
    return h;
  };
  auto minor = good;
  store_le<std::uint16_t>(minor, 10, 7);
  EXPECT_TRUE(parse_file_header(reseal(minor))) << "a 1.0 reader reads a 1.7 file";
  auto major = good;
  store_le<std::uint16_t>(major, 8, 2);
  EXPECT_EQ(parse_file_header(reseal(major)).error(), FormatError::bad_version);
  auto flags = good;
  store_le<std::uint32_t>(flags, 20, 1);
  EXPECT_EQ(parse_file_header(reseal(flags)).error(), FormatError::bad_field);
  auto bit = good;
  bit[40] ^= std::byte{1};
  EXPECT_EQ(parse_file_header(bit).error(), FormatError::bad_header_crc);
  EXPECT_EQ(parse_file_header(std::span{good}.first(good.size() - 1)).error(), FormatError::too_short);
  EXPECT_EQ(parse_file_header(std::span{good}.first(10)).error(), FormatError::too_short);
}

TEST(ListMode, RecordsRoundTripExceptForTheEnergyQuantum) {
  // REQ: SRS-LMF-004
  const std::vector<Coincidence> in{
      pair(-5'000, 0, 18431, 0),                                         // negative times are allowed
      pair(-5'000, 7, 8, 4000, 0.0F, 2047.96875F),                       // largest energy
      pair(1'000, 12, 13, -250),                                         // dt may be negative
      pair(-5'000 + 0xFFFF'FFFFLL, 1, 2, 100'000, 510.99F, 300.0F, CoincidenceKind::delayed),
  };
  const auto f = write_file(in, 16);
  ASSERT_EQ(f.block_offsets.size(), 1U) << "the last record is exactly 2^32 - 1 ps after the first";
  const auto out = read_all(f.bytes);
  ASSERT_EQ(out.size(), in.size());
  for (std::size_t i = 0; i < in.size(); ++i) {
    EXPECT_EQ(out[i].first.time, in[i].first.time);
    EXPECT_EQ(out[i].second.time, in[i].second.time);
    EXPECT_EQ(out[i].first.crystal, in[i].first.crystal);
    EXPECT_EQ(out[i].second.crystal, in[i].second.crystal);
    EXPECT_EQ(out[i].kind, in[i].kind);
    EXPECT_NEAR(out[i].first.energy.count(), in[i].first.energy.count(), 1.0 / 64.0);
    EXPECT_NEAR(out[i].second.energy.count(), in[i].second.energy.count(), 1.0 / 64.0);
  }
}

TEST(ListMode, TagsShareTheRecordStream) {
  // REQ: SRS-LMF-004
  std::vector<std::byte> buf(block_bytes(8));
  BlockWriter w{buf, 0, 8};
  ASSERT_EQ(w.append(pair(100, 1, 2, 50)), BlockWriter::Append::ok);
  ASSERT_EQ(w.append(Tag{static_cast<std::uint16_t>(TagKind::gate), Picoseconds{150}, 3}), BlockWriter::Append::ok);
  ASSERT_EQ(w.append(Tag{static_cast<std::uint16_t>(TagKind::time_mark), Picoseconds{200}, -7}),
            BlockWriter::Append::ok);
  ASSERT_EQ(w.append(Tag{4000, Picoseconds{300}, 0}), BlockWriter::Append::ok);  // a site-specific kind
  EXPECT_EQ(w.append(Tag{0, Picoseconds{300}, 0}), BlockWriter::Append::invalid);
  const auto n = w.finish(true);
  const auto b = parse_block(std::span{buf}.first(n));
  ASSERT_TRUE(b);
  ASSERT_EQ(b->record_count(), 4U);
  EXPECT_TRUE(b->end_of_run());
  EXPECT_FALSE(decode_record(*b, 0).is_tag);
  EXPECT_EQ(decode_record(*b, 1).tag, (Tag{1, Picoseconds{150}, 3}));
  EXPECT_EQ(decode_record(*b, 2).tag, (Tag{2, Picoseconds{200}, -7}));
  EXPECT_EQ(decode_record(*b, 3).tag, (Tag{4000, Picoseconds{300}, 0}));
}

TEST(ListMode, ABlockClosesWhenFullOutOfTimeRangeOrOnATimeReset) {
  // REQ: SRS-LMF-005
  std::vector<std::byte> buf(block_bytes(2));
  BlockWriter w{buf, 0, 2};
  EXPECT_EQ(w.append(pair(1'000, 1, 2, 0)), BlockWriter::Append::ok);
  EXPECT_EQ(w.append(pair(999, 1, 2, 0)), BlockWriter::Append::time_reset);
  EXPECT_EQ(w.append(pair(1'000 + 0x1'0000'0000LL, 1, 2, 0)), BlockWriter::Append::time_range);
  EXPECT_EQ(w.append(pair(1'000, 1, 2, 0)), BlockWriter::Append::ok);  // equal times are in order
  EXPECT_EQ(w.append(pair(1'001, 1, 2, 0)), BlockWriter::Append::full);
  EXPECT_EQ(w.records(), 2U);
  // Never encodable, whatever block it goes to.
  BlockWriter e{buf, 1, 2};
  EXPECT_EQ(e.append(pair(0, 0x7FFF, 2, 0)), BlockWriter::Append::invalid);
  EXPECT_EQ(e.append(pair(0, 1, 0x7FFF, 0)), BlockWriter::Append::invalid);
  EXPECT_EQ(e.append(pair(0, 1, 2, std::int64_t{1} << 31)), BlockWriter::Append::invalid);
  EXPECT_EQ(e.records(), 0U);
  // Energies outside 0 .. 2047.97 keV are clamped and counted.
  EXPECT_EQ(e.append(pair(0, 1, 2, 0, -3.0F, 5000.0F)), BlockWriter::Append::ok);
  EXPECT_EQ(e.energies_clamped(), 2U);
}

TEST(ListMode, ReaderReturnsEveryRecordOfAnIntactFile) {
  // REQ: SRS-LMF-006
  const auto in = stream(5000, 1);
  const auto f = write_file(in, 256);
  Reader r{f.bytes};
  const auto out = read_all(f.bytes, &r);
  EXPECT_EQ(out.size(), in.size());
  EXPECT_TRUE(r.issues().empty());
  EXPECT_EQ(r.stats().blocks, f.block_offsets.size());
  EXPECT_EQ(r.stats().records, in.size());
  EXPECT_EQ(r.stats().bytes_skipped, 0U);
  EXPECT_TRUE(r.stats().end_of_run);
}

TEST(ListMode, OneCorruptByteCostsOneBlockAndNothingElse) {
  // REQ: SRS-LMF-006
  const auto in = stream(1200, 2);
  const auto f = write_file(in, 100);
  ASSERT_GE(f.block_offsets.size(), 12U);
  std::mt19937_64 rng{3};
  std::uniform_int_distribution<std::size_t> where(f.block_offsets.front(), f.bytes.size() - 1);
  for (int trial = 0; trial < 400; ++trial) {
    auto bytes = f.bytes;
    const auto at = where(rng);
    bytes[at] ^= static_cast<std::byte>(1U << (trial % 8));
    Reader r{bytes};
    std::vector<Coincidence> out;
    BlockView b;
    while (r.next(b)) {
      for (std::size_t i = 0; i < b.record_count(); ++i) {
        out.push_back(decode_record(b, i).event);
      }
    }
    // The damaged block, and how many records it held.
    std::size_t k = 0;
    while (k + 1 < f.block_offsets.size() && f.block_offsets[k + 1] <= at) {
      ++k;
    }
    const bool last = k + 1 == f.block_offsets.size();
    const std::size_t lost = load_le<std::uint32_t>(f.bytes, f.block_offsets[k] + 8);
    // A damaged payload is one issue; a damaged header is two (the damage, then
    // the gap in the sequence numbers), or one if no block follows to show the gap.
    EXPECT_GE(r.issues().size(), 1U) << "byte " << at;
    EXPECT_LE(r.issues().size(), 2U) << "byte " << at;
    EXPECT_EQ(r.issues().front().offset, f.block_offsets[k]) << "byte " << at;
    EXPECT_EQ(r.stats().blocks, f.block_offsets.size() - 1) << "byte " << at;
    EXPECT_EQ(r.stats().blocks_lost, last && r.issues().front().error != FormatError::bad_payload_crc ? 0U : 1U)
        << "byte " << at;
    EXPECT_FALSE(last && r.stats().end_of_run) << "byte " << at;
    ASSERT_EQ(out.size(), in.size() - lost) << "byte " << at;
    std::size_t j = 0;
    for (const auto& c : out) {
      while (j < in.size() && in[j].first.time != c.first.time) {
        ++j;
      }
      ASSERT_LT(j, in.size()) << "byte " << at << ": a record that was never written";
      EXPECT_EQ(in[j].first.crystal, c.first.crystal);
      ++j;
    }
  }
}

TEST(ListMode, ReaderResynchronizesAfterADamagedHeader) {
  // REQ: SRS-LMF-006
  const auto in = stream(1000, 4);
  const auto f = write_file(in, 100);
  auto bytes = f.bytes;
  const auto third = f.block_offsets[2];
  bytes[third + 9] ^= std::byte{0xFF};  // record_count of block 2
  Reader r{bytes};
  const auto out = read_all(bytes, &r);
  ASSERT_EQ(r.issues().size(), 2U);
  EXPECT_EQ(r.issues()[0], (ReadIssue{third, FormatError::bad_header_crc}));
  EXPECT_EQ(r.issues()[1], (ReadIssue{f.block_offsets[3], FormatError::sequence_gap}));
  EXPECT_EQ(r.stats().blocks_lost, 1U);
  EXPECT_EQ(r.stats().bytes_skipped, f.block_offsets[3] - third);
  EXPECT_EQ(out.size(), in.size() - 100);
  EXPECT_TRUE(r.stats().end_of_run) << "the run's last block is intact";
}

TEST(ListMode, ATruncatedFileIsReadUpToItsLastCompleteBlock) {
  // REQ: SRS-LMF-007
  const auto in = stream(1000, 5);
  const auto f = write_file(in, 100);
  for (const std::size_t cut : {f.block_offsets[4] + 1, f.block_offsets[4] + 31, f.block_offsets[4] + 33,
                                f.block_offsets[5] - 1}) {
    Reader r{std::span{f.bytes}.first(cut)};
    const auto out = read_all(std::span{f.bytes}.first(cut), &r);
    EXPECT_EQ(out.size(), 400U) << "cut at " << cut;
    ASSERT_EQ(r.issues().size(), 1U) << "cut at " << cut;
    EXPECT_EQ(r.issues()[0], (ReadIssue{f.block_offsets[4], FormatError::truncated})) << "cut at " << cut;
    EXPECT_FALSE(r.stats().end_of_run) << "a crash leaves no end-of-run block";
  }
  Reader exact{std::span{f.bytes}.first(f.block_offsets[4])};
  EXPECT_EQ(read_all(std::span{f.bytes}.first(f.block_offsets[4]), &exact).size(), 400U);
  EXPECT_TRUE(exact.issues().empty());
  EXPECT_FALSE(exact.stats().end_of_run);
}

TEST(ListMode, ADamagedFileHeaderStopsTheReader) {
  // REQ: SRS-LMF-007
  auto f = write_file(stream(10, 6), 100);
  f.bytes[3] = std::byte{'X'};
  Reader r{f.bytes};
  EXPECT_EQ(r.header().error(), FormatError::bad_magic);
  BlockView b;
  EXPECT_FALSE(r.next(b));
}

TEST(ListMode, ReadsAFileWrittenByAnIndependentImplementation) {
  // REQ: SRS-LMF-008
  // fuzz/corpus/listmode/three_blocks.mdql was written from the specification
  // with Python's struct and zlib.crc32, not with this code.
  std::ifstream in{std::string{MINIDAQ_SOURCE_DIR} + "/fuzz/corpus/listmode/three_blocks.mdql", std::ios::binary};
  ASSERT_TRUE(in);
  std::vector<char> raw{std::istreambuf_iterator<char>{in}, std::istreambuf_iterator<char>{}};
  const auto file = std::as_bytes(std::span{raw});
  Reader r{file};
  ASSERT_TRUE(r.header());
  EXPECT_EQ(r.header()->metadata, R"({"format":"MDQ-L1"})");
  std::vector<Record> recs;
  BlockView b;
  while (r.next(b)) {
    for (std::size_t i = 0; i < b.record_count(); ++i) {
      recs.push_back(decode_record(b, i));
    }
  }
  EXPECT_TRUE(r.issues().empty());
  EXPECT_EQ(r.stats().blocks, 3U);
  EXPECT_TRUE(r.stats().end_of_run);
  ASSERT_EQ(recs.size(), 5U);
  EXPECT_EQ(recs[0].event, pair(1'000'000'000, 1, 2, 300, 511.0F, 480.0F));
  EXPECT_EQ(recs[1].event, pair(1'000'001'000, 5, 6, 100'250, 500.0F, 510.0F, CoincidenceKind::delayed));
  EXPECT_EQ(recs[2].tag, (Tag{1, Picoseconds{1'000'002'000}, 3}));
  EXPECT_EQ(recs[3].event, pair(1'000'005'000, 100, 18431, 0, 450.0F, 520.0F));
  EXPECT_EQ(recs[4].tag, (Tag{2, Picoseconds{1'004'005'000}, 17}));
}
