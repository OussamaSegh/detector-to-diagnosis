// A minimal generator, the shape of C++23's std::generator<T> (GCC 14), for a library without
// it. It is given, not part of the exercise: Chapter F2 explains each part.
#pragma once

#include <coroutine>
#include <exception>
#include <iterator>
#include <optional>
#include <utility>

namespace ex {

// [snippet:generator]
template <typename T>
class Generator {
 public:
  // [snippet:promise]
  struct promise_type {
    std::optional<T> value;
    std::exception_ptr error;

    Generator get_return_object() { return Generator{Handle::from_promise(*this)}; }
    std::suspend_always initial_suspend() noexcept { return {}; }  // lazy: nothing runs yet
    std::suspend_always final_suspend() noexcept { return {}; }
    std::suspend_always yield_value(T v) {  // co_yield v: store it and pause
      value = std::move(v);
      return {};
    }
    void return_void() noexcept {}
    void unhandled_exception() noexcept { error = std::current_exception(); }
  };
  using Handle = std::coroutine_handle<promise_type>;
  // [/snippet:promise]

  class iterator {
   public:
    using value_type = T;
    using difference_type = std::ptrdiff_t;
    iterator() = default;
    explicit iterator(Handle h) : h_{h} {}
    const T& operator*() const { return *h_.promise().value; }
    iterator& operator++() {
      resume(h_);  // run the coroutine body up to its next co_yield
      return *this;
    }
    void operator++(int) { ++*this; }
    friend bool operator==(const iterator& i, std::default_sentinel_t) {
      return !i.h_ || i.h_.done();
    }

   private:
    Handle h_{};
  };

  explicit Generator(Handle h) : h_{h} {}
  Generator(Generator&& o) noexcept : h_{std::exchange(o.h_, {})} {}
  Generator& operator=(Generator&& o) noexcept {
    if (this != &o) {
      if (h_) h_.destroy();
      h_ = std::exchange(o.h_, {});
    }
    return *this;
  }
  Generator(const Generator&) = delete;
  Generator& operator=(const Generator&) = delete;
  ~Generator() {
    if (h_) h_.destroy();  // destroys the coroutine's frame and its local variables
  }

  iterator begin() {
    resume(h_);
    return iterator{h_};
  }
  std::default_sentinel_t end() const noexcept { return {}; }

 private:
  static void resume(Handle h) {
    h.resume();
    if (h.promise().error) std::rethrow_exception(h.promise().error);
  }
  Handle h_;
};
// [/snippet:generator]

}  // namespace ex
