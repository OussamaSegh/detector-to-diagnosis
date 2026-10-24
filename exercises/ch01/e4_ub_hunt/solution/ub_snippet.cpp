// Exercise 1.4 solution: the same five functions without undefined behavior.
#include "ub_snippet.hpp"

#include <cstring>
#include <limits>

namespace ex {

// Bug 1 (signed overflow): `total += f` overflows int64 before the check runs,
// and the optimizer may delete `total < 0` because overflow "cannot happen".
// Fix: check before adding (or use __builtin_add_overflow).
std::int64_t total_duration_saturating(std::span<const std::int64_t> frames_ps) {
  constexpr auto max = std::numeric_limits<std::int64_t>::max();
  std::int64_t total = 0;
  for (const std::int64_t f : frames_ps) {
    if (f > 0 && total > max - f) {
      return max;
    }
    total += f;
  }
  return total;
}

// Bug 2 (out of bounds): `bin > size()` lets bin == 1024 through. Fix: >=.
void fill_energy_histogram(std::array<std::uint32_t, 1024>& hist, std::initializer_list<float> energies_kev) {
  for (const float e : energies_kev) {
    // Also guard the float -> size_t conversion: negative or huge values are UB.
    std::size_t bin = hist.size() - 1;
    if (e >= 0.0F && e < static_cast<float>(hist.size())) {
      bin = static_cast<std::size_t>(e);
    }
    ++hist[bin];
  }
}

// Bug 3 (use after free): `first` refers into the vector; emplace_back
// reallocates and frees the old storage. Fix: copy before growing.
std::string label_and_extend(std::vector<std::string>& names, int extra) {
  std::string first = names.front();
  for (int i = 0; i < extra; ++i) {
    names.emplace_back("placeholder-name-long-enough-to-allocate");
  }
  return first;
}

// Bug 4 (misaligned access and strict aliasing): dereferencing a uint64_t*
// that points at an odd address, into storage that holds bytes, not a uint64_t.
// Fix: memcpy (compiles to one unaligned load on x86-64 and ARMv8).
std::uint64_t read_word(const std::byte* p) {
  std::uint64_t w;
  std::memcpy(&w, p, sizeof w);
  return w;
}

// Bug 5 (invalid shift): `1` is an int; shifting it by >= 31 is UB.
// Fix: shift a 64-bit one.
std::uint64_t channel_mask(unsigned channel) {
  return std::uint64_t{1} << channel;
}

}  // namespace ex
