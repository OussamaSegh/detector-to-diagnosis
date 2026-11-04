// SPDX-License-Identifier: MIT
// The tests of window, run by CTest: window_test sums | edges. Exit 0 when they pass.
#include <cstdio>
#include <cstring>
#include <vector>

#include "window.hpp"

namespace {

int check(bool ok, const char* what) {
  if (!ok) {
    std::printf("FAILED: %s\n", what);
  }
  return ok ? 0 : 1;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc != 2) {
    return 2;
  }
  if (std::strcmp(argv[1], "sums") == 0) {
    const std::vector<std::int64_t> want{6, 9, 12};
    return check(window::sums({1, 2, 3, 4, 5}, 3) == want, "sums of 3 over 1..5");
  }
  if (std::strcmp(argv[1], "edges") == 0) {
    return check(window::sums({1, 2}, 0).empty(), "width 0") +
           check(window::sums({1, 2}, 3).empty(), "width larger than the history") +
           check(window::sums({7}, 1) == std::vector<std::int64_t>{7}, "one count");
  }
  return 2;
}
