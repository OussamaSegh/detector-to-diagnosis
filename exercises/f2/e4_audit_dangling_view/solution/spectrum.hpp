// Exercise F2.4 (audit), solution: a view must view something that outlives it.
#pragma once

#include <cstddef>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace ex {

class Spectrum {
 public:
  Spectrum(std::string material, std::vector<int> counts)
      : material_{std::move(material)}, counts_{std::move(counts)} {}

  [[nodiscard]] std::vector<int> counts() const { return counts_; }

  // [snippet:fixed]
  // A view into the member, valid while the Spectrum lives and is not changed.
  [[nodiscard]] std::span<const int> peak_region(std::size_t first, std::size_t last) const {
    if (first > last || last > counts_.size()) throw std::out_of_range{"peak region"};
    return std::span<const int>{counts_}.subspan(first, last - first);
  }

  // A new string: the text does not exist anywhere until this function builds it.
  [[nodiscard]] std::string label() const { return material_ + " spectrum"; }
  // [/snippet:fixed]

  [[nodiscard]] std::span<const int> storage() const noexcept { return counts_; }

 private:
  std::string material_;
  std::vector<int> counts_;
};

}  // namespace ex
