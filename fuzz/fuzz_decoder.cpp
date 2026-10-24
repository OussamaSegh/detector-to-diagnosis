// SPDX-License-Identifier: MIT
// Fuzz target: the packed-word stream decoder (Chapter 7).
//
// Besides "does not crash" (ASan, UBSan), it checks properties that must hold
// for any input: every word is accounted for, every single written is valid,
// valid words survive a decode/encode round trip, and decoding bytes in
// arbitrary chunks gives the same result as decoding the words in one call.
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <algorithm>
#include <cstring>
#include <span>
#include <vector>

#include "minidaq/core/bits.hpp"
#include "minidaq/core/geometry.hpp"
#include "minidaq/format/packed_single.hpp"

using namespace minidaq;

namespace {

void check(bool ok) {
  if (!ok) {
    std::abort();  // libFuzzer reports the input that got here
  }
}

}  // namespace

// [snippet:target]
extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data, std::size_t size) {
  if (size < 1) {
    return 0;
  }
  const std::size_t chunk = 1 + data[0] % 64;  // first byte: how the bytes arrive
  const auto* bytes = reinterpret_cast<const std::byte*>(data + 1);
  const std::size_t nbytes = size - 1;
  const std::size_t nwords = nbytes / 8;

  std::vector<std::uint64_t> words(nwords);
  for (std::size_t i = 0; i < nwords; ++i) {
    std::uint64_t w;
    std::memcpy(&w, bytes + i * 8, 8);
    words[i] = from_little_endian(w);
  }

  // Reference: one call over all words.
  packed::StreamDecoder ref{ScannerGeometry::num_crystals};
  std::vector<Single> a(nwords);
  const std::size_t na = ref.decode(words, a);
  check(na <= nwords);
  check(ref.stats().words == nwords);
  check(ref.stats().words == na + ref.stats().invalid_crystal);
  std::size_t k = 0;
  for (std::size_t i = 0; i < nwords; ++i) {
    const packed::Fields f = packed::unpack(words[i]);
    if (f.crystal >= ScannerGeometry::num_crystals) {
      continue;
    }
    const Single& s = a[k++];
    check(s.crystal.value() == f.crystal);
    check(s.energy.count() >= 0.0F && s.energy.count() <= packed::energy_max_kev);
    check(packed::encode(s) == words[i]);  // lossless for every valid word
  }
  check(k == na);

  // The same bytes in chunks of `chunk` bytes: identical singles and counts.
  packed::StreamDecoder chunked{ScannerGeometry::num_crystals};
  std::vector<Single> b(nwords);
  std::size_t nb = 0;
  std::vector<std::byte> carry;
  for (std::size_t pos = 0; pos < nbytes; pos += chunk) {
    const std::size_t len = std::min(chunk, nbytes - pos);
    carry.insert(carry.end(), bytes + pos, bytes + pos + len);
    const std::size_t whole = carry.size() / 8 * 8;
    nb += chunked.decode_bytes(std::span{carry}.first(whole), std::span{b}.subspan(nb));
    carry.erase(carry.begin(), carry.begin() + static_cast<std::ptrdiff_t>(whole));
  }
  check(nb == na);
  check(std::equal(a.begin(), a.begin() + static_cast<std::ptrdiff_t>(na), b.begin()));
  return 0;
}
// [/snippet:target]
