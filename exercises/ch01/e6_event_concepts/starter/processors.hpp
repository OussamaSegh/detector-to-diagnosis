#pragma once
// Exercise 1.6 starter. TODO: write the two concepts and constrain feed().
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
concept SingleSink = true;  // TODO

template <typename T>
concept SingleFilter = true;  // TODO

template <typename T>
inline constexpr bool is_sink_v = SingleSink<T>;
template <typename T>
inline constexpr bool is_filter_v = SingleFilter<T>;

template <typename F, typename S>
std::uint64_t feed(std::span<const Single> in, F& filter, S& sink) {
  (void)in;
  (void)filter;
  (void)sink;
  return 0;  // TODO
}

}  // namespace ex
