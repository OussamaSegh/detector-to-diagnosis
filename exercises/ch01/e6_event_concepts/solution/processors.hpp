#pragma once
// Exercise 1.6 solution. See NOTES.md.
#include <concepts>
#include <cstdint>
#include <span>

namespace ex {

struct Single {
  std::int64_t time_ps;
  std::uint32_t crystal;
  float energy_kev;
};

template <typename T>
concept SingleSink = requires(T& t, const T& ct, const Single& s) {
  t.consume(s);
  { ct.count() } -> std::convertible_to<std::uint64_t>;
};

template <typename T>
concept SingleFilter = requires(const T& f, const Single& s) {
  { f.accept(s) } -> std::same_as<bool>;
};

template <typename T>
inline constexpr bool is_sink_v = SingleSink<T>;
template <typename T>
inline constexpr bool is_filter_v = SingleFilter<T>;

template <SingleFilter F, SingleSink S>
std::uint64_t feed(std::span<const Single> in, const F& filter, S& sink) {
  std::uint64_t accepted = 0;
  for (const Single& s : in) {
    if (filter.accept(s)) {
      sink.consume(s);
      ++accepted;
    }
  }
  return accepted;
}

}  // namespace ex
