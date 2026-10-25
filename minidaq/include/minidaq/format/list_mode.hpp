// SPDX-License-Identifier: MIT
// MiniDAQ - the list-mode file format, MDQ-L1 (Chapter 12).
//
// A list-mode file is a file header followed by blocks of 16-byte records,
// one record per coincidence or tag, in time order. All fields are
// little-endian. The full specification, with the rules for readers and
// writers, is docs/formats/mdq-l1.md; this header is its implementation.
//
// File header (header_bytes long, a multiple of 8):
//
//  offset  size  field
//       0     8  magic           0x4D 0x44 0x51 0x4C 0x0D 0x0A 0x1A 0x0A ("MDQL\r\n\x1a\n")
//       8     2  major           1: a reader rejects any other major version
//      10     2  minor           0: a 1.x reader reads any 1.y file
//      12     4  header_bytes    40 + metadata_bytes rounded up to a multiple of 8
//      16     4  metadata_bytes  length of the UTF-8 JSON metadata
//      20     4  flags           must be 0 in version 1.0
//      24     4  record_bytes    16
//      28     4  reserved        must be 0
//      32     m  metadata        JSON, then zero bytes up to a multiple of 8
//   32+m'     4  header_crc      CRC-32 of every byte before it
//   36+m'     4  reserved        must be 0
//
// Block (32 + 16 * record_count bytes):
//
//       0     4  magic           "MDQB" (0x4D 0x44 0x51 0x42)
//       4     4  sequence        0 for the first block of every file, +1 per block
//       8     4  record_count    0 .. max_block_records
//      12     4  flags           bit 0: last block of the run; other bits must be 0
//      16     8  base_time_ps    signed; the time of the block's first record
//      24     4  payload_crc     CRC-32 of the records
//      28     4  header_crc      CRC-32 of bytes 0 .. 27
//      32  16*n  records
//
// Record (16 bytes):
//
//       0     4  time_offset     ps after base_time_ps (unsigned)
//       4     2  crystal_a       bits 0-14: crystal of the earlier single; bit 15: delayed
//       6     2  crystal_b       crystal of the later single
//       8     4  dt_ps           signed: second.time - first.time
//      12     2  energy_a        1/32 keV, 0 .. 65535 (2047.97 keV)
//      14     2  energy_b
//
// A record whose crystal_a is 0x7FFF is a tag: crystal_b is the tag kind,
// dt_ps its value, and both energies are 0. Records are in nondecreasing time
// order within a block. A writer that receives an earlier record closes the
// block, so a time reset (a clock restart) shows as a block whose base time is
// earlier than the last record of the block before it.
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string_view>
#include <vector>

#include "minidaq/core/expected.hpp"
#include "minidaq/core/single.hpp"

namespace minidaq::listmode {

// [snippet:constants]
inline constexpr std::array<std::byte, 8> file_magic{std::byte{'M'}, std::byte{'D'}, std::byte{'Q'},
                                                     std::byte{'L'}, std::byte{0x0D}, std::byte{0x0A},
                                                     std::byte{0x1A}, std::byte{0x0A}};
inline constexpr std::array<std::byte, 4> block_magic{std::byte{'M'}, std::byte{'D'}, std::byte{'Q'},
                                                      std::byte{'B'}};
inline constexpr std::uint16_t version_major = 1;
inline constexpr std::uint16_t version_minor = 0;
inline constexpr std::size_t file_header_fixed_bytes = 32;
inline constexpr std::size_t block_header_bytes = 32;
inline constexpr std::size_t record_bytes = 16;
inline constexpr std::size_t max_block_records = 65536;  // 1 MiB of records; a reader's sanity limit
inline constexpr std::size_t max_metadata_bytes = 1U << 20;
inline constexpr std::uint32_t block_flag_end_of_run = 0x1;
inline constexpr std::uint16_t tag_crystal = 0x7FFF;  // crystal_a of a tag record
inline constexpr std::uint16_t delayed_bit = 0x8000;
inline constexpr float energy_lsb_kev = 1.0F / 32.0F;
// [/snippet:constants]

// The size of a block holding n records.
[[nodiscard]] constexpr std::size_t block_bytes(std::size_t n) noexcept { return block_header_bytes + n * record_bytes; }

// [snippet:tags]
// What a tag marks. Kind 0 is invalid, kinds 1 .. 1023 are reserved for this
// specification, and 1024 .. 65535 are free for site-specific use. A reader
// skips a kind it does not know.
// NOLINTNEXTLINE(performance-enum-size): the kind is a 16-bit field on disk
enum class TagKind : std::uint16_t {
  gate = 1,       // a physiological trigger (ECG R wave, respiratory phase); value: the gate channel
  time_mark = 2,  // a periodic mark from the acquisition clock; value: the mark's index
};

struct Tag {
  std::uint16_t kind = 0;  // a TagKind, or a kind this program does not know
  Picoseconds time{};
  std::int32_t value = 0;
  friend bool operator==(const Tag&, const Tag&) = default;
};
// [/snippet:tags]

enum class FormatError : std::uint8_t {
  too_short,          // fewer bytes than the structure needs
  bad_magic,          // not the expected magic
  bad_version,        // a major version this program does not read
  bad_header_crc,     // the CRC of a header does not match
  bad_field,          // a size, a flag or a reserved field has a value the specification forbids
  bad_payload_crc,    // the block header is intact but its records are not
  truncated,          // the block's records run past the end of the data
  sequence_gap,       // blocks are missing between two intact blocks
};
inline constexpr std::size_t num_format_errors = 8;
[[nodiscard]] std::string_view to_string(FormatError e) noexcept;

// ---------------------------------------------------------------------------
// File header

struct FileHeader {
  std::uint16_t major = version_major;
  std::uint16_t minor = version_minor;
  std::size_t header_bytes = 0;
  std::string_view metadata;  // points into the caller's buffer
};

// The header for `metadata` (UTF-8 JSON, not checked here). Allocates: called
// once per file. Empty if the metadata is longer than max_metadata_bytes.
[[nodiscard]] std::vector<std::byte> encode_file_header(std::string_view metadata);

// Checks the magic, the version, the sizes and the CRC. Never reads past `data`.
[[nodiscard]] Expected<FileHeader, FormatError> parse_file_header(std::span<const std::byte> data) noexcept;

// ---------------------------------------------------------------------------
// Writing blocks

// [snippet:writer]
// Fills one block in a buffer the caller owns (a buffer from the sink's pool,
// so the records are written once, where the I/O thread will read them).
// append() either writes the record or says why it belongs in the next block;
// finish() writes the header and the two CRCs and returns the block's size.
class BlockWriter {
 public:
  enum class Append : std::uint8_t {
    ok,          // written
    full,        // the block has max_records records
    time_range,  // the record is more than 2^32 - 1 ps after the block's base time
    time_reset,  // the record is earlier than the previous one
    invalid,     // a crystal id >= 0x7FFF or a time difference outside int32: never encodable
  };

  // buffer.size() must be at least block_bytes(max_records); max_records in
  // 1 .. max_block_records.
  BlockWriter(std::span<std::byte> buffer, std::uint32_t sequence, std::size_t max_records) noexcept;

  [[nodiscard]] Append append(const Coincidence& c) noexcept;
  [[nodiscard]] Append append(const Tag& t) noexcept;
  [[nodiscard]] std::size_t finish(bool end_of_run) noexcept;

  [[nodiscard]] std::size_t records() const noexcept { return count_; }
  [[nodiscard]] std::uint64_t energies_clamped() const noexcept { return clamped_; }

 private:
  [[nodiscard]] Append place(Picoseconds time) noexcept;
  std::span<std::byte> buffer_;
  std::uint32_t sequence_;
  std::size_t max_records_;
  std::size_t count_ = 0;
  Picoseconds base_{};
  Picoseconds last_{};
  std::uint64_t clamped_ = 0;
};
// [/snippet:writer]

// ---------------------------------------------------------------------------
// Reading blocks

struct BlockView {
  std::size_t offset = 0;  // of the block header, from the start of the data
  std::uint32_t sequence = 0;
  std::uint32_t flags = 0;
  Picoseconds base_time{};
  std::span<const std::byte> records;  // record_count * 16 bytes, CRC checked

  [[nodiscard]] std::size_t record_count() const noexcept { return records.size() / record_bytes; }
  [[nodiscard]] bool end_of_run() const noexcept { return (flags & block_flag_end_of_run) != 0; }
};

// Parses and checks one block at the start of `data` (header and payload CRC).
[[nodiscard]] Expected<BlockView, FormatError> parse_block(std::span<const std::byte> data) noexcept;

// One decoded record.
struct Record {
  bool is_tag = false;
  Coincidence event;  // valid if !is_tag; energies quantized to 1/32 keV
  Tag tag;            // valid if is_tag
};
[[nodiscard]] Record decode_record(const BlockView& block, std::size_t i) noexcept;

struct ReadIssue {
  std::size_t offset = 0;
  FormatError error = FormatError::too_short;
  friend bool operator==(const ReadIssue&, const ReadIssue&) = default;
};

// [snippet:reader_stats]
struct ReaderStats {
  std::uint64_t blocks = 0;          // intact blocks returned
  std::uint64_t records = 0;         // records in them
  std::uint64_t blocks_lost = 0;     // sequence numbers never seen, plus blocks with a bad payload
  std::uint64_t records_lost = 0;    // records in blocks whose payload CRC failed
  std::uint64_t bytes_skipped = 0;   // bytes that belonged to no intact block
  bool end_of_run = false;           // the last intact block closed the run
};
// [/snippet:reader_stats]

// Walks the blocks of a whole file held in memory (read or mapped). A damaged
// block is reported, not fatal: the reader resynchronizes on the next block
// magic whose header CRC is valid, so one bad sector costs the blocks it
// touches and nothing after them.
class Reader {
 public:
  explicit Reader(std::span<const std::byte> file) noexcept;

  // The file header, or why it could not be read. If it failed, next()
  // returns false at once: without the header the record size is unknown.
  [[nodiscard]] const Expected<FileHeader, FormatError>& header() const noexcept { return header_; }

  // The next intact block; false at the end of the data.
  [[nodiscard]] bool next(BlockView& out);

  [[nodiscard]] const std::vector<ReadIssue>& issues() const noexcept { return issues_; }
  [[nodiscard]] const ReaderStats& stats() const noexcept { return stats_; }

 private:
  void resync(std::size_t from);
  std::span<const std::byte> data_;
  Expected<FileHeader, FormatError> header_;
  std::size_t pos_ = 0;
  std::uint32_t next_sequence_ = 0;  // every file starts at 0, so a lost first block is seen too
  std::vector<ReadIssue> issues_;
  ReaderStats stats_;
};

}  // namespace minidaq::listmode
