// Exercise 1.4 starter: five functions, five undefined-behavior bugs.
// Use the sanitizers to find them before you read the code.
#include "ub_snippet.hpp"

#include <limits>

namespace ex {

std::int64_t total_duration_saturating(std::span<const std::int64_t> frames_ps) {
  std::int64_t total = 0;
  for (const std::int64_t f : frames_ps) {
    total += f;
    if (total < 0) {  // "detect" overflow after the fact
      return std::numeric_limits<std::int64_t>::max();
    }
  }
  return total;
}

void fill_energy_histogram(std::array<std::uint32_t, 1024>& hist, std::initializer_list<float> energies_kev) {
  for (const float e : energies_kev) {
    auto bin = static_cast<std::size_t>(e);
    if (bin > hist.size()) {
      bin = hist.size() - 1;
    }
    ++hist.data()[bin];
  }
}

std::string label_and_extend(std::vector<std::string>& names, int extra) {
  const std::string& first = names.front();
  for (int i = 0; i < extra; ++i) {
    names.emplace_back("placeholder-name-long-enough-to-allocate");
  }
  return first;
}

std::uint64_t read_word(const std::byte* p) {
  return *reinterpret_cast<const std::uint64_t*>(p);
}

std::uint64_t channel_mask(unsigned channel) {
  return static_cast<std::uint64_t>(1 << channel);
}

}  // namespace ex
