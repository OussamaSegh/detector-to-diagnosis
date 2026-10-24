// SPDX-License-Identifier: MIT
// Exercise 3.6 solution.
#pragma once

#include <condition_variable>
#include <deque>
#include <functional>
#include <mutex>
#include <stop_token>
#include <thread>

namespace ex {

class Worker {
 public:
  explicit Worker(std::function<void(int)> handler) : handler_{std::move(handler)} {
    thread_ = std::jthread([this](std::stop_token st) { run(st); });
  }
  ~Worker() { stop(); }
  Worker(const Worker&) = delete;
  Worker& operator=(const Worker&) = delete;

  bool submit(int item) {
    {
      std::lock_guard lock{m_};
      if (stopping_) {
        return false;
      }
      q_.push_back(item);
    }
    cv_.notify_one();
    return true;
  }

  void stop() {
    {
      std::lock_guard lock{m_};
      stopping_ = true;  // refuse new work from now on
    }
    thread_.request_stop();  // wakes the wait below through the stop_token
    if (thread_.joinable()) {
      thread_.join();
    }
  }

 private:
  void run(std::stop_token st) {
    std::unique_lock lock{m_};
    for (;;) {
      // Returns when there is work, or when a stop was requested.
      cv_.wait(lock, st, [&] { return !q_.empty(); });
      if (q_.empty()) {
        return;  // stop requested and nothing left to drain
      }
      const int item = q_.front();
      q_.pop_front();
      lock.unlock();
      handler_(item);  // never call user code while holding the lock
      lock.lock();
    }
  }

  std::function<void(int)> handler_;
  std::mutex m_;
  std::condition_variable_any cv_;
  std::deque<int> q_;
  bool stopping_ = false;
  std::jthread thread_;  // last member: started after everything it uses exists
};

}  // namespace ex
