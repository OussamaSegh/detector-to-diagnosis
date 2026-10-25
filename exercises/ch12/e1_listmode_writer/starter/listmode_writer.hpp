// SPDX-License-Identifier: MIT
// Exercise 12.1: a list-mode writer and reader for MDQ-L1, written from the
// specification (docs/formats/mdq-l1.md) without minidaq::listmode.
#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <string_view>
#include <vector>

#include "minidaq/core/single.hpp"

namespace ex121 {

// A whole file: the header with `metadata`, the coincidences in blocks of at
// most records_per_block records, then an empty closing block flagged end of
// run. A block also ends when the next record's time offset would not fit in
// 32 bits.
[[nodiscard]] std::vector<std::byte> write_file(std::string_view metadata,
                                                std::span<const minidaq::Coincidence> events,
                                                std::size_t records_per_block);

struct ReadResult {
  bool header_ok = false;   // magic, a major version of 1, sizes and CRC all good
  std::uint16_t minor = 0;
  std::string metadata;
  std::vector<minidaq::Coincidence> events;  // from intact blocks only
  std::vector<std::size_t> bad_blocks;       // byte offsets of blocks whose payload CRC failed
  bool damaged_header = false;               // a block header was damaged: reading stopped there
  bool end_of_run = false;                   // the last block read closed the run
};

[[nodiscard]] ReadResult read_file(std::span<const std::byte> file);

}  // namespace ex121
