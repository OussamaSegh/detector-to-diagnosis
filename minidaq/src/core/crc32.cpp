// SPDX-License-Identifier: MIT
#include "minidaq/core/crc32.hpp"

namespace minidaq {

namespace {

std::uint32_t byte_at(std::span<const std::byte> d, std::size_t i) noexcept {
  return std::to_integer<std::uint32_t>(d[i]);
}

}  // namespace

// [snippet:update]
std::uint32_t crc32_update(std::uint32_t crc, std::span<const std::byte> data) noexcept {
  const auto& t = detail::crc32_tables;
  std::uint32_t c = ~crc;
  std::size_t i = 0;
  // Eight bytes per step: the first four are folded into the running CRC,
  // the next four are looked up directly. Bytes are read one at a time, so
  // the code needs no alignment and gives the same result on any byte order.
  for (; i + 8 <= data.size(); i += 8) {
    const std::uint32_t lo = c ^ (byte_at(data, i) | (byte_at(data, i + 1) << 8U) |
                                  (byte_at(data, i + 2) << 16U) | (byte_at(data, i + 3) << 24U));
    c = t[7][lo & 0xFFU] ^ t[6][(lo >> 8U) & 0xFFU] ^ t[5][(lo >> 16U) & 0xFFU] ^ t[4][lo >> 24U] ^
        t[3][byte_at(data, i + 4)] ^ t[2][byte_at(data, i + 5)] ^ t[1][byte_at(data, i + 6)] ^
        t[0][byte_at(data, i + 7)];
  }
  for (; i < data.size(); ++i) {
    c = (c >> 8U) ^ t[0][(c ^ byte_at(data, i)) & 0xFFU];
  }
  return ~c;
}
// [/snippet:update]

std::uint32_t crc32_bytewise(std::span<const std::byte> data) noexcept {
  std::uint32_t c = 0xFFFFFFFFU;
  for (std::size_t i = 0; i < data.size(); ++i) {
    c = (c >> 8U) ^ detail::crc32_tables[0][(c ^ byte_at(data, i)) & 0xFFU];
  }
  return ~c;
}

}  // namespace minidaq
