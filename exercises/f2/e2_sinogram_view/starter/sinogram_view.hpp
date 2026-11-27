// Exercise F2.2, starter: a two-dimensional view over a flat buffer, in the shape of
// std::mdspan. The extents are stored; the indexing, the row and the checks are yours.
#pragma once

#include <cstddef>
#include <span>
#include <stdexcept>

namespace ex {

template <typename T>
class SinogramView {
 public:
  SinogramView(std::span<T> data, std::size_t angles, std::size_t bins)
      : data_{data}, angles_{angles}, bins_{bins} {
    // TODO: reject a buffer whose size is not angles * bins (std::invalid_argument).
  }

  // TODO: row-major: the bins of one angle are contiguous. Uses C++23's operator[] with two
  // arguments.
  T& operator[](std::size_t angle, std::size_t bin) const noexcept { return data_[0]; }

  // TODO: the same, with a bounds check (std::out_of_range).
  T& at(std::size_t angle, std::size_t bin) const { return data_[0]; }

  // TODO: the bins of one angle, as a span into the buffer.
  std::span<T> row(std::size_t angle) const { return {}; }

  [[nodiscard]] std::size_t angles() const noexcept { return angles_; }
  [[nodiscard]] std::size_t bins() const noexcept { return bins_; }
  [[nodiscard]] std::size_t size() const noexcept { return data_.size(); }

 private:
  std::span<T> data_;
  std::size_t angles_;
  std::size_t bins_;
};

}  // namespace ex
