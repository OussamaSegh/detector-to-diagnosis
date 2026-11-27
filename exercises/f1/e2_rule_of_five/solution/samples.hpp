// Exercise F1.2, solution: a buffer that owns a raw array, with the rule of five written out.
#pragma once

#include <algorithm>
#include <cstddef>
#include <utility>

namespace ex {

// [snippet:five]
class Samples {
 public:
  explicit Samples(std::size_t n) : data_{n != 0 ? new double[n]{} : nullptr}, size_{n} {
    if (n != 0) count_new();
  }
  ~Samples() { release(); }

  // 1. Copy constructor: a new array of our own, then copy the values.
  Samples(const Samples& other) : Samples{other.size_} {
    std::copy(other.data_, other.data_ + other.size_, data_);
  }
  // 2. Copy assignment: copy and swap. The copy may throw; if it does, *this is unchanged.
  Samples& operator=(const Samples& other) {
    if (this != &other) {
      Samples tmp{other};
      swap(tmp);
    }
    return *this;
  }
  // 3. Move constructor: take the pointer, leave the source empty.
  Samples(Samples&& other) noexcept
      : data_{std::exchange(other.data_, nullptr)}, size_{std::exchange(other.size_, 0)} {}
  // 4. Move assignment: free ours, take theirs.
  Samples& operator=(Samples&& other) noexcept {
    if (this != &other) {
      release();
      data_ = std::exchange(other.data_, nullptr);
      size_ = std::exchange(other.size_, 0);
    }
    return *this;
  }
  // 5. The destructor is release().

  void swap(Samples& other) noexcept {
    std::swap(data_, other.data_);
    std::swap(size_, other.size_);
  }
  // [/snippet:five]

  [[nodiscard]] std::size_t size() const noexcept { return size_; }
  double& operator[](std::size_t i) noexcept { return data_[i]; }
  const double& operator[](std::size_t i) const noexcept { return data_[i]; }

  // Counters for the tests: arrays allocated so far, and arrays not yet freed.
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
