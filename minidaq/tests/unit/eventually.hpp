// SPDX-License-Identifier: MIT
// Waiting in tests (Chapter 16, CAPA-0001; coding standard rule 5.5). A test waits for the
// condition that it needs, never for a fixed time: on a slow or busy machine a sleep is too
// short and the test fails although the code is right. The deadline only turns a hang into a
// failure, so it is long; a slow machine makes the test slower, never red.
#pragma once

#include <chrono>
#include <thread>

namespace minidaq::test_support {

// [snippet:eventually]
inline constexpr std::chrono::seconds patience{10};

// True as soon as done() is true; false if it is still false after the deadline.
template <class Done>
[[nodiscard]] bool eventually(Done done, std::chrono::steady_clock::duration deadline = patience) {
  const auto end = std::chrono::steady_clock::now() + deadline;
  while (!done()) {
    if (std::chrono::steady_clock::now() >= end) {
      return done();
    }
    std::this_thread::sleep_for(std::chrono::milliseconds{1});
  }
  return true;
}
// [/snippet:eventually]

}  // namespace minidaq::test_support
