// SPDX-License-Identifier: MIT
// Fuzz target: the MDQ-L1 list-mode reader (Chapter 12).
//
// The input is a list-mode file, valid or not. Properties checked for any input:
//  - the reader never reads out of bounds and always terminates;
//  - every byte after the file header is either in an intact block that was
//    returned or counted as skipped, never both and never neither;
//  - decoding is stable: a returned block's records, encoded again by the
//    writer and decoded, give the same records. (Bytes can differ: a forged
//    block may have a base time before its first record, or nonzero energies
//    in a tag, and the writer produces neither.)
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <span>
#include <vector>

#include "minidaq/format/list_mode.hpp"

using namespace minidaq;
using namespace minidaq::listmode;

namespace {

void check(bool ok) {
  if (!ok) {
    std::abort();  // libFuzzer reports the input that got here
  }
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data, std::size_t size) {
  const std::span<const std::byte> file{reinterpret_cast<const std::byte*>(data), size};
  Reader r{file};
  if (!r.header()) {
    BlockView b;
    check(!r.next(b));
    return 0;
  }
  std::size_t in_blocks = 0;
  std::vector<std::byte> buf;
  BlockView b;
  while (r.next(b)) {
    const std::size_t n = b.record_count();
    in_blocks += block_bytes(n);
    check(b.offset + block_bytes(n) <= size);
    // Records the writer refuses (a crystal of 0x7FFF with the delayed bit, a tag
    // of kind 0, times out of order) cannot come from MiniDAQ but can be forged
    // with valid CRCs; such a block is not re-encoded.
    const std::size_t cap = n == 0 ? 1 : n;
    buf.assign(block_bytes(cap), std::byte{0});
    BlockWriter w{buf, b.sequence, cap};
    bool encodable = true;
    for (std::size_t i = 0; i < n && encodable; ++i) {
      const auto rec = decode_record(b, i);
      encodable = (rec.is_tag ? w.append(rec.tag) : w.append(rec.event)) == BlockWriter::Append::ok;
    }
    if (encodable) {
      const auto again = parse_block(std::span<const std::byte>{buf}.first(w.finish(b.end_of_run())));
      check(static_cast<bool>(again) && again->record_count() == n && again->sequence == b.sequence);
      for (std::size_t i = 0; i < n; ++i) {
        const auto x = decode_record(b, i);
        const auto y = decode_record(*again, i);
        check(x.is_tag == y.is_tag && (x.is_tag ? x.tag == y.tag : x.event == y.event));
      }
    }
  }
  check(r.header()->header_bytes + in_blocks + r.stats().bytes_skipped == size);
  return 0;
}
