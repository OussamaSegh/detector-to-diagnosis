// SPDX-License-Identifier: MIT
// Exercise 29.2: work shared between threads, as the C++ backprojector shares its lines.
#pragma once

#include <cstddef>
#include <span>
#include <vector>

namespace ex {

// Calls body(first, last, thread) for contiguous chunks that cover [0, count) exactly once, one
// chunk per thread, on min(threads, count) threads (at least one call, for count = 0 too).
// threads = 0 means one thread.
template <typename Body>
void parallel_for(std::size_t count, unsigned threads, const Body& body);

// out[index[i]] += value[i] for every i, computed on `threads` threads, for an output of `size`
// values. The result is the same on every run with the same number of threads, and differs
// between thread counts only by rounding. Throws std::out_of_range for an index >= size.
std::vector<double> scatter_add(std::span<const std::size_t> index,
                                std::span<const double> value, std::size_t size,
                                unsigned threads);

}  // namespace ex

#include "parallel_impl.hpp"
