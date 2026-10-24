// SPDX-License-Identifier: MIT
// Exercise 3.6 starter: this version cannot be stopped while it waits.
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
      q_.push_back(item);
    }
    cv_.notify_one();
    return true;
  }

  void stop() {
    thread_.request_stop();
    if (thread_.joinable()) {
      thread_.join();
    }
  }

 private:
  void run(std::stop_token st) {
    std::unique_lock lock{m_};
    while (!st.stop_requested()) {
      cv_.wait(lock, [&] { return !q_.empty(); });  // BUG: never wakes up for a stop
      const int item = q_.front();
      q_.pop_front();
      lock.unlock();
      handler_(item);
      lock.lock();
    }
  }

  std::function<void(int)> handler_;
  std::mutex m_;
  std::condition_variable cv_;
  std::deque<int> q_;
  std::jthread thread_;  // last member: started after everything it uses exists
};

}  // namespace ex
