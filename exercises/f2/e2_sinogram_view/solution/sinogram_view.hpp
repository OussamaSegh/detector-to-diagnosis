// Exercise F2.2, solution: a two-dimensional view of a sinogram in the shape of std::mdspan
// (C++23): a pointer and two extents, row-major, with C++23's multidimensional operator[].
#pragma once

#include <cstddef>
#include <span>
#include <stdexcept>

namespace ex {

// [snippet:view]
template <typename T>
class SinogramView {
 public:
  SinogramView(std::span<T> data, std::size_t angles, std::size_t bins)
      : data_{data}, angles_{angles}, bins_{bins} {
    if (data.size() != angles * bins) throw std::invalid_argument{"buffer size != angles * bins"};
  }

  // Row-major (std::layout_right): the bins of one angle are contiguous.
  T& operator[](std::size_t angle, std::size_t bin) const noexcept {
    return data_[angle * bins_ + bin];
  }

  T& at(std::size_t angle, std::size_t bin) const {
    if (angle >= angles_ || bin >= bins_) throw std::out_of_range{"sinogram index"};
    return (*this)[angle, bin];
  }

  std::span<T> row(std::size_t angle) const { return data_.subspan(angle * bins_, bins_); }
  // [/snippet:view]

  [[nodiscard]] std::size_t angles() const noexcept { return angles_; }
  [[nodiscard]] std::size_t bins() const noexcept { return bins_; }
  [[nodiscard]] std::size_t size() const noexcept { return data_.size(); }

 private:
  std::span<T> data_;
  std::size_t angles_;
  std::size_t bins_;
};

}  // namespace ex
