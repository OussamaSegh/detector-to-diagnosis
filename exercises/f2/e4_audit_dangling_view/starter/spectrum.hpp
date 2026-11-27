// Exercise F2.4 (audit), starter: the recorded change of CHANGE.md, as it was proposed.
#pragma once

#include <cstddef>
#include <span>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace ex {

class Spectrum {
 public:
  Spectrum(std::string material, std::vector<int> counts)
      : material_{std::move(material)}, counts_{std::move(counts)} {}

  // A copy of the counts, for callers that keep them.
  [[nodiscard]] std::vector<int> counts() const { return counts_; }

  // [snippet:change]
  // The counts of bins [first, last), without a copy.
  std::span<const int> peak_region(std::size_t first, std::size_t last) const {
    return std::span<const int>{counts()}.subspan(first, last - first);
  }

  // "LSO spectrum", for the plot title.
  std::string_view label() const { return material_ + " spectrum"; }
  // [/snippet:change]

  // For the tests: the storage the spectrum owns.
  [[nodiscard]] std::span<const int> storage() const noexcept { return counts_; }

 private:
  std::string material_;
  std::vector<int> counts_;
};

}  // namespace ex
