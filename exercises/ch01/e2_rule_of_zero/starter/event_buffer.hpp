#pragma once
// Exercise 1.2 starter: legacy raw-pointer buffer. TODO: refactor to the Rule of 0.
#include <cstddef>
#include <cstdint>
#include <span>

namespace ex {

struct Single {
  std::int64_t time_ps;
  std::uint32_t crystal;
  float energy_kev;
};

class EventBuffer {
 public:
  explicit EventBuffer(std::size_t capacity)
      : data_{new Single[capacity]}, size_{0}, capacity_{capacity} {}
  ~EventBuffer() { delete[] data_; }
  // BUG (on purpose): the implicit copy constructor and copy assignment copy
  // the pointer, so two buffers delete the same array.

  bool push(const Single& s) {
    if (size_ == capacity_) {
      return false;
    }
    data_[size_++] = s;
    return true;
  }
  [[nodiscard]] std::size_t size() const { return size_; }
  [[nodiscard]] std::size_t capacity() const { return capacity_; }
  [[nodiscard]] std::span<const Single> view() const { return {data_, size_}; }

 private:
  Single* data_;
  std::size_t size_;
  std::size_t capacity_;
};

}  // namespace ex
