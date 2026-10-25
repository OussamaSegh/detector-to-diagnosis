// SPDX-License-Identifier: MIT
#include "listmode_writer.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

#include "minidaq/core/byte_io.hpp"
#include "minidaq/core/crc32.hpp"

namespace ex121 {

using minidaq::load_le;
using minidaq::store_le;

namespace {

constexpr std::size_t block_header = 32;
constexpr std::size_t record = 16;

std::uint16_t energy_code(minidaq::KeV e) {
  const float q = std::round(e.count() * 32.0F);
  return q <= 0.0F ? std::uint16_t{0} : q >= 65535.0F ? std::uint16_t{0xFFFF} : static_cast<std::uint16_t>(q);
}

// Writes the header of the block that starts at `at` and holds n records.
void seal_block(std::vector<std::byte>& out, std::size_t at, std::uint32_t sequence, std::size_t n,
                std::uint32_t flags, std::int64_t base) {
  const std::span<std::byte> b{out};
  std::copy_n("MDQB", 4, reinterpret_cast<char*>(out.data() + at));  // NOLINT(cppcoreguidelines-pro-type-reinterpret-cast)
  store_le<std::uint32_t>(b, at + 4, sequence);
  store_le<std::uint32_t>(b, at + 8, static_cast<std::uint32_t>(n));
  store_le<std::uint32_t>(b, at + 12, flags);
  store_le<std::uint64_t>(b, at + 16, static_cast<std::uint64_t>(base));
  // [snippet:crc]
  // The payload CRC covers the records only; the header CRC covers the 28
  // header bytes before it, payload CRC included.
  store_le<std::uint32_t>(b, at + 24, minidaq::crc32(b.subspan(at + block_header, n * record)));
  store_le<std::uint32_t>(b, at + 28, minidaq::crc32(b.subspan(at, 28)));
  // [/snippet:crc]
}

}  // namespace

std::vector<std::byte> write_file(std::string_view metadata, std::span<const minidaq::Coincidence> events,
                                  std::size_t records_per_block) {
  // File header: 32 fixed bytes, the metadata padded to 8, the CRC and 4 zero bytes.
  const std::size_t meta_end = 32 + (metadata.size() + 7) / 8 * 8;
  std::vector<std::byte> out(meta_end + 8, std::byte{0});
  std::copy_n("MDQL\r\n\x1a\n", 8, reinterpret_cast<char*>(out.data()));  // NOLINT(cppcoreguidelines-pro-type-reinterpret-cast)
  const std::span<std::byte> h{out};
  store_le<std::uint16_t>(h, 8, 1);
  store_le<std::uint16_t>(h, 10, 0);
  store_le<std::uint32_t>(h, 12, static_cast<std::uint32_t>(out.size()));
  store_le<std::uint32_t>(h, 16, static_cast<std::uint32_t>(metadata.size()));
  store_le<std::uint32_t>(h, 24, 16);
  std::copy(metadata.begin(), metadata.end(), reinterpret_cast<char*>(out.data() + 32));  // NOLINT(cppcoreguidelines-pro-type-reinterpret-cast)
  store_le<std::uint32_t>(h, meta_end, minidaq::crc32(h.first(meta_end)));

  std::uint32_t sequence = 0;
  std::size_t block_at = out.size();
  std::size_t n = 0;
  std::int64_t base = 0;
  out.resize(out.size() + block_header);
  // [snippet:append]
  for (const auto& c : events) {
    const std::int64_t t = c.first.time.count();
    // A new block when this one is full or the offset would not fit in 32 bits.
    if (n == records_per_block || (n > 0 && t - base > std::int64_t{std::numeric_limits<std::uint32_t>::max()})) {
      seal_block(out, block_at, sequence++, n, 0, base);
      block_at = out.size();
      n = 0;
      out.resize(out.size() + block_header);
    }
    if (n == 0) {
      base = t;  // offsets are from the block's first record, not the file's
    }
    const std::size_t at = out.size();
    out.resize(at + record);
    const std::span<std::byte> r{out};
    const auto delayed = c.kind == minidaq::CoincidenceKind::delayed ? 0x8000U : 0U;
    store_le<std::uint32_t>(r, at, static_cast<std::uint32_t>(t - base));
    store_le<std::uint16_t>(r, at + 4, static_cast<std::uint16_t>(c.first.crystal.value() | delayed));
    store_le<std::uint16_t>(r, at + 6, static_cast<std::uint16_t>(c.second.crystal.value()));
    store_le<std::uint32_t>(r, at + 8, static_cast<std::uint32_t>(static_cast<std::int32_t>(c.time_difference().count())));
    store_le<std::uint16_t>(r, at + 12, energy_code(c.first.energy));
    store_le<std::uint16_t>(r, at + 14, energy_code(c.second.energy));
    ++n;
  }
  // [/snippet:append]
  if (n > 0) {
    seal_block(out, block_at, sequence++, n, 0, base);
    block_at = out.size();
    out.resize(out.size() + block_header);
  }
  seal_block(out, block_at, sequence, 0, 1, 0);  // the closing block: end of run
  return out;
}

ReadResult read_file(std::span<const std::byte> file) {
  ReadResult res;
  if (file.size() < 32 || !std::equal(file.begin(), file.begin() + 8, reinterpret_cast<const std::byte*>("MDQL\r\n\x1a\n"))) {  // NOLINT(cppcoreguidelines-pro-type-reinterpret-cast)
    return res;
  }
  // [snippet:version]
  // Major versions are incompatible; a 1.x reader reads any 1.y file.
  if (load_le<std::uint16_t>(file, 8) != 1) {
    return res;
  }
  // [/snippet:version]
  res.minor = load_le<std::uint16_t>(file, 10);
  const std::size_t header_bytes = load_le<std::uint32_t>(file, 12);
  const std::size_t meta = load_le<std::uint32_t>(file, 16);
  if (header_bytes != 32 + (meta + 7) / 8 * 8 + 8 || file.size() < header_bytes ||
      minidaq::crc32(file.first(header_bytes - 8)) != load_le<std::uint32_t>(file, header_bytes - 8)) {
    return res;
  }
  res.header_ok = true;
  res.metadata.assign(reinterpret_cast<const char*>(file.data() + 32), meta);  // NOLINT(cppcoreguidelines-pro-type-reinterpret-cast)

  std::size_t pos = header_bytes;
  while (pos + block_header <= file.size()) {
    const auto h = file.subspan(pos, block_header);
    if (!std::equal(h.begin(), h.begin() + 4, reinterpret_cast<const std::byte*>("MDQB")) ||  // NOLINT(cppcoreguidelines-pro-type-reinterpret-cast)
        minidaq::crc32(h.first(28)) != load_le<std::uint32_t>(h, 28)) {
      res.damaged_header = true;  // the size is unknown: nothing after this can be trusted to be where it seems
      return res;
    }
    const std::size_t n = load_le<std::uint32_t>(h, 8);
    const auto base = static_cast<std::int64_t>(load_le<std::uint64_t>(h, 16));
    if (file.size() - pos - block_header < n * record) {
      res.damaged_header = true;  // truncated
      return res;
    }
    const auto payload = file.subspan(pos + block_header, n * record);
    // [snippet:check]
    if (minidaq::crc32(payload) != load_le<std::uint32_t>(h, 24)) {
      res.bad_blocks.push_back(pos);  // the header is intact, so the next block is where it says
      res.end_of_run = false;
      pos += block_header + n * record;
      continue;
    }
    // [/snippet:check]
    for (std::size_t i = 0; i < n; ++i) {
      const auto r = payload.subspan(i * record, record);
      const auto a = load_le<std::uint16_t>(r, 4);
      if (a == 0x7FFFU) {
        continue;  // a tag
      }
      const std::int64_t t = base + std::int64_t{load_le<std::uint32_t>(r, 0)};
      const auto dt = static_cast<std::int32_t>(load_le<std::uint32_t>(r, 8));
      minidaq::Coincidence c;
      c.first = {minidaq::Picoseconds{t}, minidaq::CrystalId{a & 0x7FFFU},
                 minidaq::KeV{static_cast<float>(load_le<std::uint16_t>(r, 12)) / 32.0F}};
      c.second = {minidaq::Picoseconds{t + dt}, minidaq::CrystalId{load_le<std::uint16_t>(r, 6)},
                  minidaq::KeV{static_cast<float>(load_le<std::uint16_t>(r, 14)) / 32.0F}};
      c.kind = (a & 0x8000U) != 0 ? minidaq::CoincidenceKind::delayed : minidaq::CoincidenceKind::prompt;
      res.events.push_back(c);
    }
    res.end_of_run = (load_le<std::uint32_t>(h, 12) & 1U) != 0;
    pos += block_header + n * record;
  }
  return res;
}

}  // namespace ex121
