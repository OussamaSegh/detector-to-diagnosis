// Exercise F1.2, starter: a buffer that owns a raw array. It has a destructor and nothing else,
// so the compiler writes the copy operations, and they copy the pointer, not the array.
// Write the other four special members (the rule of five).
#pragma once

#include <algorithm>
#include <cstddef>
#include <utility>

namespace ex {

class Samples {
 public:
  explicit Samples(std::size_t n) : data_{n != 0 ? new double[n]{} : nullptr}, size_{n} {
    if (n != 0) count_new();
  }
  ~Samples() { release(); }

  // TODO: copy constructor (deep copy, one allocation).
  // TODO: copy assignment (deep, safe against self-assignment; copy and swap is the easy way).
  // TODO: move constructor and move assignment, noexcept, leaving the source empty.

  [[nodiscard]] std::size_t size() const noexcept { return size_; }
  double& operator[](std::size_t i) noexcept { return data_[i]; }
  const double& operator[](std::size_t i) const noexcept { return data_[i]; }

  static long allocations() noexcept { return counters().made; }
  static long live() noexcept { return counters().made - counters().freed; }

 private:
  struct Counters {
    long made = 0;
    long freed = 0;
  };
  static Counters& counters() noexcept {
    static Counters c;
    return c;
  }
  static void count_new() noexcept { ++counters().made; }
  void release() noexcept {
    if (data_ != nullptr) {
      delete[] data_;
      ++counters().freed;
      data_ = nullptr;
    }
    size_ = 0;
  }

  double* data_ = nullptr;
  std::size_t size_ = 0;
};

}  // namespace ex
