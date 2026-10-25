// SPDX-License-Identifier: MIT
#include "minidaq/format/list_mode.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

#include "minidaq/core/byte_io.hpp"
#include "minidaq/core/crc32.hpp"

namespace minidaq::listmode {

namespace {

constexpr std::size_t pad8(std::size_t n) noexcept { return (n + 7U) & ~std::size_t{7}; }

std::uint16_t quantize_energy(KeV e, std::uint64_t& clamped) noexcept {
  const float q = std::round(e.count() / energy_lsb_kev);
  if (!(q >= 0.0F)) {  // also catches NaN
    ++clamped;
    return 0;
  }
  if (q > 65535.0F) {
    ++clamped;
    return 0xFFFF;
  }
  return static_cast<std::uint16_t>(q);
}

}  // namespace

std::string_view to_string(FormatError e) noexcept {
  switch (e) {
    case FormatError::too_short: return "too_short";
    case FormatError::bad_magic: return "bad_magic";
    case FormatError::bad_version: return "bad_version";
    case FormatError::bad_header_crc: return "bad_header_crc";
    case FormatError::bad_field: return "bad_field";
    case FormatError::bad_payload_crc: return "bad_payload_crc";
    case FormatError::truncated: return "truncated";
    case FormatError::sequence_gap: return "sequence_gap";
  }
  return "unknown";
}

// ---------------------------------------------------------------------------
// File header

std::vector<std::byte> encode_file_header(std::string_view metadata) {
  if (metadata.size() > max_metadata_bytes) {
    return {};
  }
  const std::size_t meta_end = file_header_fixed_bytes + pad8(metadata.size());
  std::vector<std::byte> out(meta_end + 8, std::byte{0});
  const std::span<std::byte> b{out};
  std::copy(file_magic.begin(), file_magic.end(), b.begin());
  store_le<std::uint16_t>(b, 8, version_major);
  store_le<std::uint16_t>(b, 10, version_minor);
  store_le<std::uint32_t>(b, 12, static_cast<std::uint32_t>(out.size()));
  store_le<std::uint32_t>(b, 16, static_cast<std::uint32_t>(metadata.size()));
  store_le<std::uint32_t>(b, 20, 0);
  store_le<std::uint32_t>(b, 24, static_cast<std::uint32_t>(record_bytes));
  store_le<std::uint32_t>(b, 28, 0);
  std::transform(metadata.begin(), metadata.end(), b.begin() + file_header_fixed_bytes,
                 [](char c) { return static_cast<std::byte>(c); });
  store_le<std::uint32_t>(b, meta_end, crc32(b.first(meta_end)));
  return out;
}

// [snippet:parse_header]
Expected<FileHeader, FormatError> parse_file_header(std::span<const std::byte> data) noexcept {
  if (data.size() < file_header_fixed_bytes) {
    return Unexpected{FormatError::too_short};
  }
  if (!std::equal(file_magic.begin(), file_magic.end(), data.begin())) {
    return Unexpected{FormatError::bad_magic};
  }
  // The version comes first: a later major version may lay out the rest differently.
  FileHeader h;
  h.major = load_le<std::uint16_t>(data, 8);
  h.minor = load_le<std::uint16_t>(data, 10);
  if (h.major != version_major) {
    return Unexpected{FormatError::bad_version};
  }
  // Then the sizes that locate the CRC, then the CRC, then everything else:
  // a damaged header is reported as damaged, not as a strange value.
  h.header_bytes = load_le<std::uint32_t>(data, 12);
  const std::size_t meta = load_le<std::uint32_t>(data, 16);
  if (meta > max_metadata_bytes || h.header_bytes != file_header_fixed_bytes + pad8(meta) + 8) {
    return Unexpected{FormatError::bad_field};
  }
  if (data.size() < h.header_bytes) {
    return Unexpected{FormatError::too_short};
  }
  const std::size_t crc_at = h.header_bytes - 8;
  if (crc32(data.first(crc_at)) != load_le<std::uint32_t>(data, crc_at)) {
    return Unexpected{FormatError::bad_header_crc};
  }
  const bool padding_zero = std::all_of(data.begin() + static_cast<std::ptrdiff_t>(file_header_fixed_bytes + meta),
                                        data.begin() + static_cast<std::ptrdiff_t>(crc_at),
                                        [](std::byte b) { return b == std::byte{0}; });
  if (load_le<std::uint32_t>(data, 20) != 0 || load_le<std::uint32_t>(data, 24) != record_bytes ||
      load_le<std::uint32_t>(data, 28) != 0 || load_le<std::uint32_t>(data, crc_at + 4) != 0 || !padding_zero) {
    return Unexpected{FormatError::bad_field};
  }
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast): bytes viewed as the UTF-8 text they hold
  h.metadata = std::string_view{reinterpret_cast<const char*>(data.data() + file_header_fixed_bytes), meta};
  return h;
}
// [/snippet:parse_header]

// ---------------------------------------------------------------------------
// Writing blocks

BlockWriter::BlockWriter(std::span<std::byte> buffer, std::size_t max_records) noexcept
    : buffer_{buffer},
      max_records_{std::min({max_records, max_block_records,
                             buffer.size() < block_header_bytes ? 0 : (buffer.size() - block_header_bytes) / record_bytes})} {}

// [snippet:place]
BlockWriter::Append BlockWriter::place(Picoseconds time) noexcept {
  if (count_ == max_records_) {
    return Append::full;
  }
  if (count_ == 0) {
    base_ = time;
  } else if (time < last_) {
    return Append::time_reset;
  } else if (time.count() - base_.count() > std::int64_t{std::numeric_limits<std::uint32_t>::max()}) {
    return Append::time_range;
  }
  last_ = time;
  return Append::ok;
}
// [/snippet:place]

// [snippet:append]
BlockWriter::Append BlockWriter::append(const Coincidence& c) noexcept {
  const auto a = c.first.crystal.value();
  const auto b = c.second.crystal.value();
  const auto dt = c.time_difference().count();
  if (a >= tag_crystal || b >= tag_crystal || dt < std::numeric_limits<std::int32_t>::min() ||
      dt > std::numeric_limits<std::int32_t>::max()) {
    return Append::invalid;
  }
  if (const auto r = place(c.first.time); r != Append::ok) {
    return r;
  }
  const std::size_t at = block_bytes(count_);
  const auto delayed = c.kind == CoincidenceKind::delayed ? delayed_bit : std::uint16_t{0};
  store_le<std::uint32_t>(buffer_, at, static_cast<std::uint32_t>(c.first.time.count() - base_.count()));
  store_le<std::uint16_t>(buffer_, at + 4, static_cast<std::uint16_t>(a | delayed));
  store_le<std::uint16_t>(buffer_, at + 6, static_cast<std::uint16_t>(b));
  store_le<std::uint32_t>(buffer_, at + 8, static_cast<std::uint32_t>(static_cast<std::int32_t>(dt)));
  store_le<std::uint16_t>(buffer_, at + 12, quantize_energy(c.first.energy, clamped_));
  store_le<std::uint16_t>(buffer_, at + 14, quantize_energy(c.second.energy, clamped_));
  ++count_;
  return Append::ok;
}
// [/snippet:append]

BlockWriter::Append BlockWriter::append(const Tag& t) noexcept {
  if (t.kind == 0) {
    return Append::invalid;
  }
  if (const auto r = place(t.time); r != Append::ok) {
    return r;
  }
  const std::size_t at = block_bytes(count_);
  store_le<std::uint32_t>(buffer_, at, static_cast<std::uint32_t>(t.time.count() - base_.count()));
  store_le<std::uint16_t>(buffer_, at + 4, tag_crystal);
  store_le<std::uint16_t>(buffer_, at + 6, t.kind);
  store_le<std::uint32_t>(buffer_, at + 8, static_cast<std::uint32_t>(t.value));
  store_le<std::uint32_t>(buffer_, at + 12, 0);
  ++count_;
  return Append::ok;
}

// [snippet:finish]
std::size_t BlockWriter::finish(std::uint32_t sequence, std::uint32_t flags) noexcept {
  const std::size_t bytes = block_bytes(count_);
  std::copy(block_magic.begin(), block_magic.end(), buffer_.begin());
  store_le<std::uint32_t>(buffer_, 4, sequence);
  store_le<std::uint32_t>(buffer_, 8, static_cast<std::uint32_t>(count_));
  store_le<std::uint32_t>(buffer_, 12, flags);
  store_le<std::uint64_t>(buffer_, 16, static_cast<std::uint64_t>(count_ == 0 ? 0 : base_.count()));
  store_le<std::uint32_t>(buffer_, 24, crc32(buffer_.subspan(block_header_bytes, bytes - block_header_bytes)));
  store_le<std::uint32_t>(buffer_, 28, crc32(buffer_.first(28)));
  return bytes;
}
// [/snippet:finish]

// ---------------------------------------------------------------------------
// Reading blocks

namespace {

bool block_header_intact(std::span<const std::byte> data) noexcept {
  return data.size() >= block_header_bytes && std::equal(block_magic.begin(), block_magic.end(), data.begin()) &&
         crc32(data.first(28)) == load_le<std::uint32_t>(data, 28);
}

}  // namespace

// [snippet:parse_block]
Expected<BlockView, FormatError> parse_block(std::span<const std::byte> data) noexcept {
  if (data.size() < block_header_bytes) {
    return Unexpected{FormatError::too_short};
  }
  if (!std::equal(block_magic.begin(), block_magic.end(), data.begin())) {
    return Unexpected{FormatError::bad_magic};
  }
  if (crc32(data.first(28)) != load_le<std::uint32_t>(data, 28)) {
    return Unexpected{FormatError::bad_header_crc};
  }
  BlockView v;
  v.sequence = load_le<std::uint32_t>(data, 4);
  const std::size_t n = load_le<std::uint32_t>(data, 8);
  v.flags = load_le<std::uint32_t>(data, 12);
  v.base_time = Picoseconds{static_cast<std::int64_t>(load_le<std::uint64_t>(data, 16))};
  if (n > max_block_records || (v.flags & ~(block_flag_end_of_run | block_flag_end_of_file)) != 0) {
    return Unexpected{FormatError::bad_field};
  }
  if (data.size() < block_bytes(n)) {
    return Unexpected{FormatError::truncated};
  }
  v.records = data.subspan(block_header_bytes, n * record_bytes);
  if (crc32(v.records) != load_le<std::uint32_t>(data, 24)) {
    return Unexpected{FormatError::bad_payload_crc};
  }
  return v;
}
// [/snippet:parse_block]

// [snippet:decode]
Record decode_record(const BlockView& block, std::size_t i) noexcept {
  const auto r = block.records.subspan(i * record_bytes, record_bytes);
  const Picoseconds t{block.base_time.count() + std::int64_t{load_le<std::uint32_t>(r, 0)}};
  const auto a = load_le<std::uint16_t>(r, 4);
  const auto b = load_le<std::uint16_t>(r, 6);
  const auto dt = static_cast<std::int32_t>(load_le<std::uint32_t>(r, 8));
  Record out;
  if (a == tag_crystal) {
    out.is_tag = true;
    out.tag = Tag{b, t, dt};
    return out;
  }
  out.event.kind = (a & delayed_bit) != 0 ? CoincidenceKind::delayed : CoincidenceKind::prompt;
  out.event.first = Single{t, CrystalId{std::uint32_t{a} & 0x7FFFU},
                           KeV{static_cast<float>(load_le<std::uint16_t>(r, 12)) * energy_lsb_kev}};
  out.event.second = Single{Picoseconds{t.count() + dt}, CrystalId{b},
                            KeV{static_cast<float>(load_le<std::uint16_t>(r, 14)) * energy_lsb_kev}};
  return out;
}
// [/snippet:decode]

Reader::Reader(std::span<const std::byte> file) noexcept
    : data_{file}, header_{parse_file_header(file)}, pos_{header_ ? header_->header_bytes : file.size()} {}

// [snippet:resync]
// Looks for the next block magic, from `from`, whose header CRC is valid.
// Records can contain the four magic bytes by chance; the 32-bit CRC over the
// header makes a false match about as likely as a missed corruption.
void Reader::resync(std::size_t from) {
  auto it = data_.begin() + static_cast<std::ptrdiff_t>(std::min(from, data_.size()));
  while (true) {
    it = std::search(it, data_.end(), block_magic.begin(), block_magic.end());
    if (it == data_.end()) {
      break;
    }
    const auto at = static_cast<std::size_t>(it - data_.begin());
    if (block_header_intact(data_.subspan(at))) {
      stats_.bytes_skipped += at - pos_;
      pos_ = at;
      return;
    }
    ++it;
  }
  stats_.bytes_skipped += data_.size() - pos_;
  pos_ = data_.size();
}
// [/snippet:resync]

// [snippet:next]
bool Reader::next(BlockView& out) {
  while (pos_ < data_.size()) {
    const auto rest = data_.subspan(pos_);
    auto block = parse_block(rest);
    if (!block && block.error() == FormatError::bad_payload_crc) {
      // The header is intact, so the size is known: skip exactly this block.
      const std::size_t n = load_le<std::uint32_t>(rest, 8);
      issues_.push_back({pos_, FormatError::bad_payload_crc});
      ++stats_.blocks_lost;
      stats_.records_lost += n;
      stats_.bytes_skipped += block_bytes(n);
      stats_.end_of_run = false;
      stats_.end_of_file = false;
      next_sequence_ = load_le<std::uint32_t>(rest, 4) + 1;
      pos_ += block_bytes(n);
      continue;
    }
    if (!block) {
      issues_.push_back({pos_, block.error() == FormatError::too_short ? FormatError::truncated : block.error()});
      stats_.end_of_run = false;
      stats_.end_of_file = false;
      resync(pos_ + 1);
      continue;
    }
    BlockView v = *block;
    v.offset = pos_;
    if (v.sequence != next_sequence_) {
      issues_.push_back({pos_, FormatError::sequence_gap});
      const auto gap = v.sequence - next_sequence_;  // modular: a gap across the wrap is still positive
      if (gap < (std::uint32_t{1} << 31)) {
        stats_.blocks_lost += gap;
      }
    }
    next_sequence_ = v.sequence + 1;
    pos_ += block_bytes(v.record_count());
    ++stats_.blocks;
    stats_.records += v.record_count();
    stats_.end_of_run = v.end_of_run();
    stats_.end_of_file = v.end_of_file();
    out = v;
    return true;
  }
  return false;
}
// [/snippet:next]

}  // namespace minidaq::listmode
