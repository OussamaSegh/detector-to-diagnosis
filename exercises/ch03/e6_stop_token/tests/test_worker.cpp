// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <future>
#include <memory>
#include <thread>
#include <vector>

#include "worker.hpp"

using namespace std::chrono_literals;

namespace {
// Runs f on a detached thread and fails the whole process if it does not
// finish in time: a hung stop() would otherwise hang the test run.
template <typename F>
void within(std::chrono::milliseconds limit, F f, const char* what) {
  auto done = std::make_shared<std::promise<void>>();
  auto fut = done->get_future();
  std::thread([done, f]() mutable {
    f();
    done->set_value();
  }).detach();
  if (fut.wait_for(limit) != std::future_status::ready) {
    std::fprintf(stderr, "watchdog: %s did not finish within %lld ms\n", what,
                 static_cast<long long>(limit.count()));
    std::_Exit(1);
  }
}
}  // namespace

TEST(Worker, ProcessesInOrder) {
  std::vector<int> got;
  std::mutex m;
  within(5'000ms, [&] {
    ex::Worker w{[&](int i) {
      std::lock_guard lock{m};
      got.push_back(i);
    }};
    for (int i = 0; i < 1000; ++i) {
      EXPECT_TRUE(w.submit(i));
    }
    w.stop();
  }, "ProcessesInOrder");
  std::lock_guard lock{m};
  ASSERT_EQ(got.size(), 1000U);
  for (int i = 0; i < 1000; ++i) {
    ASSERT_EQ(got[static_cast<std::size_t>(i)], i);
  }
}

TEST(Worker, StopDrainsQueuedItemsAndRefusesNewOnes) {
  std::atomic<int> handled{0};
  within(5'000ms, [&] {
    ex::Worker w{[&](int) {
      std::this_thread::sleep_for(1ms);
      handled.fetch_add(1);
    }};
    for (int i = 0; i < 50; ++i) {
      w.submit(i);
    }
    w.stop();
    EXPECT_FALSE(w.submit(99)) << "submit after stop must be refused";
  }, "StopDrains");
  EXPECT_EQ(handled.load(), 50);
}

TEST(Worker, IdleWorkerStopsPromptly) {
  within(2'000ms, [] {
    ex::Worker w{[](int) {}};
    std::this_thread::sleep_for(20ms);  // let it block in its wait
    const auto t0 = std::chrono::steady_clock::now();
    w.stop();
    const auto dt = std::chrono::steady_clock::now() - t0;
    EXPECT_LT(dt, 100ms);
  }, "IdleWorkerStopsPromptly");
}
