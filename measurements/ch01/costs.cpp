// SPDX-License-Identifier: MIT
// Chapter 1's two quoted costs, measured: a throw and catch through a few frames against a
// returned error (std::expected), each frame with a destructor, and a ranges pipeline against the
// hand-written loop. Built and run by run.sh; prints a Markdown table, the median of 11 repetitions
// of each.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <expected>
#include <iomanip>
#include <iostream>
#include <random>
#include <ranges>
#include <stdexcept>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;

volatile int sink = 0;

// A frame with a destructor, as real code has (a lock, a buffer): the compiler cannot fold the
// recursion into a loop, and unwinding must run it.
struct Frame {
  Frame() = default;
  Frame(const Frame&) = delete;
  Frame& operator=(const Frame&) = delete;
  ~Frame() { sink = sink + 1; }
};

[[gnu::noinline]] int parse_throw(int depth, int value) {
  Frame frame;
  if (depth == 0) {
    if (value < 0) throw std::runtime_error("malformed packet");
    return value;
  }
  return parse_throw(depth - 1, value) + 1;
}

[[gnu::noinline]] std::expected<int, int> parse_expected(int depth, int value) {
  Frame frame;
  if (depth == 0) {
    if (value < 0) return std::unexpected(1);
    return value;
  }
  auto r = parse_expected(depth - 1, value);
  if (!r) return r;
  return *r + 1;
}

template <class F>
double median_ns_per_call(F f, int calls) {
  std::vector<double> runs;
  for (int rep = 0; rep < 11; ++rep) {
    auto t0 = Clock::now();
    for (int i = 0; i < calls; ++i) f(i);
    auto t1 = Clock::now();
    runs.push_back(std::chrono::duration<double, std::nano>(t1 - t0).count() / calls);
  }
  std::ranges::sort(runs);
  return runs[runs.size() / 2];
}

struct Single {
  std::uint32_t crystal;
  double energy;
};

}  // namespace

int main() {
  std::cout << std::fixed << std::setprecision(1);
  std::cout << "| Error path | Frames | ns per call, error | ns per call, no error |\n";
  std::cout << "|---|---:|---:|---:|\n";
  for (int depth : {1, 10, 50}) {
    double t_err = median_ns_per_call(
        [depth](int) {
          try {
            sink = parse_throw(depth, -1);
          } catch (const std::runtime_error&) {
            sink = -1;
          }
        },
        200'000);
    double t_ok = median_ns_per_call([depth](int i) { sink = parse_throw(depth, i); }, 2'000'000);
    std::cout << "| throw and catch | " << depth << " | " << t_err << " | " << t_ok << " |\n";
    double e_err = median_ns_per_call(
        [depth](int) { sink = parse_expected(depth, -1).error_or(0); }, 2'000'000);
    double e_ok = median_ns_per_call(
        [depth](int i) { sink = parse_expected(depth, i).value_or(0); }, 2'000'000);
    std::cout << "| std::expected | " << depth << " | " << e_err << " | " << e_ok << " |\n";
  }

  std::mt19937 rng(1);
  std::uniform_real_distribution<double> energy(0.0, 700.0);
  std::vector<Single> singles(1'000'000);
  for (std::uint32_t k = 0; auto& s : singles) s = {k++ % 4096, energy(rng)};
  std::vector<std::uint32_t> out;
  out.reserve(singles.size());
  auto loop = [&](int) {
    out.clear();
    for (const auto& s : singles)
      if (s.energy >= 350.0) out.push_back(s.crystal);
    sink = static_cast<int>(out.size());
  };
  auto ranges = [&](int) {
    out.clear();
    for (auto c : singles | std::views::filter([](const Single& s) { return s.energy >= 350.0; }) |
                      std::views::transform([](const Single& s) { return s.crystal; }))
      out.push_back(c);
    sink = static_cast<int>(out.size());
  };
  std::cout << "\n| Energy filter over 1,000,000 singles | ns per single |\n|---|---:|\n";
  std::cout << "| hand-written loop | " << median_ns_per_call(loop, 20) / 1e6 << " |\n";
  std::cout << "| filter and transform views | " << median_ns_per_call(ranges, 20) / 1e6 << " |\n";
  return 0;
}
