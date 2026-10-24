#pragma once
// Exercise 1.2 solution: Rule of 0 for EventBuffer. The class declares no
// destructor, copy or move operations; its single member manages itself.
// See NOTES.md.
#include <cstddef>
#include <cstdint>
#include <span>
#include <utility>
#include <vector>

namespace ex {

struct Single {
  std::int64_t time_ps;
  std::uint32_t crystal;
  float energy_kev;
};

// A fixed-capacity owner with value semantics. It exists so that:
//  - copies keep the capacity (std::vector's copy does not promise that), and
//  - a moved-from object is guaranteed empty with capacity 0 (std::vector only
//    promises "valid but unspecified").
// This is the one place where special members are written by hand.
class FixedStorage {
 public:
  FixedStorage() = default;
  explicit FixedStorage(std::size_t capacity) { v_.reserve(capacity); }
  FixedStorage(const FixedStorage& o) {
    v_.reserve(o.v_.capacity());
    v_.assign(o.v_.begin(), o.v_.end());
  }
  FixedStorage& operator=(const FixedStorage& o) {
    if (this != &o) {
      FixedStorage tmp{o};  // copy-and-swap: strong exception guarantee
      v_.swap(tmp.v_);
    }
    return *this;
  }
  FixedStorage(FixedStorage&& o) noexcept : v_{std::exchange(o.v_, {})} {}
  FixedStorage& operator=(FixedStorage&& o) noexcept {
    v_ = std::exchange(o.v_, {});
    return *this;
  }
  ~FixedStorage() = default;

  [[nodiscard]] bool full() const noexcept { return v_.size() == v_.capacity(); }
  void push_unchecked(const Single& s) { v_.push_back(s); }
  [[nodiscard]] std::size_t size() const noexcept { return v_.size(); }
  [[nodiscard]] std::size_t capacity() const noexcept { return v_.capacity(); }
  [[nodiscard]] std::span<const Single> view() const noexcept { return v_; }

 private:
  std::vector<Single> v_;
};

class EventBuffer {
 public:
  explicit EventBuffer(std::size_t capacity) : data_{capacity} {}

  bool push(const Single& s) {
    if (data_.full()) {
      return false;  // never reallocate: capacity is part of the contract
    }
    data_.push_unchecked(s);
    return true;
  }
  [[nodiscard]] std::size_t size() const noexcept { return data_.size(); }
  [[nodiscard]] std::size_t capacity() const noexcept { return data_.capacity(); }
  [[nodiscard]] std::span<const Single> view() const noexcept { return data_.view(); }

 private:
  FixedStorage data_;  // Rule of 0: EventBuffer declares no special members
};

}  // namespace ex
