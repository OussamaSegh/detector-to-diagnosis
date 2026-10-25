// SPDX-License-Identifier: MIT
// Exercise 19.4 subject: two units that each meet their specification, put together.
//
// batches() cuts a stream of singles into batches; Pairer pairs singles that are close in time,
// fed one batch at a time, the way MiniDAQ's coincidence sorter is fed by the pipeline (Chapter
// 10, Chapter 3). Each unit has passed its own tests. What is specified about the two together:
//
//   run(singles, batch_size, window) takes singles in time order (ties in any crystal order) and
//   returns the pairs that this rule gives: take the singles in the order of (time, crystal); the
//   first single not yet used opens a window [time, time + window]; if another unused single is in
//   the window, the first such single is its partner, the pair (opener, partner) is output and both
//   are used; otherwise the opener is used alone and gives no pair. The result is the same for
//   every batch_size of 1 or more.
//
// The build defines EX_MUTANT: 0 is the subject as specified, 1 to 5 are seeded mistakes.
#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

#ifndef EX_MUTANT
#define EX_MUTANT 0
#endif

namespace ex19 {

struct Single {
  std::int64_t time;
  std::uint16_t crystal;
  friend bool operator==(const Single&, const Single&) = default;
};

struct Pair {
  Single opener;
  Single partner;
  friend bool operator==(const Pair&, const Pair&) = default;
};

// Cuts the stream into batches of batch_size singles; the last batch may be shorter.
inline std::vector<std::vector<Single>> batches(std::span<const Single> s, std::size_t batch_size) {
  std::vector<std::vector<Single>> out;
  for (std::size_t i = 0; i < s.size(); i += batch_size) {
#if EX_MUTANT == 3
    if (i + batch_size > s.size()) {
      break;
    }
#endif
    std::size_t end = std::min(s.size(), i + batch_size);
#if EX_MUTANT == 4
    if (end < s.size()) {
      ++end;
    }
#endif
    out.emplace_back(s.begin() + static_cast<std::ptrdiff_t>(i), s.begin() + static_cast<std::ptrdiff_t>(end));
  }
  return out;
}

class Pairer {
 public:
  explicit Pairer(std::int64_t window) : window_{window} {}

  // Takes the next batch; returns the pairs of the openers whose windows have closed.
  std::vector<Pair> push(std::span<const Single> batch) {
    batch_start_ = buf_.size();
    for (const Single& s : batch) {
      insert(s);
    }
    std::vector<Pair> out;
    while (!buf_.empty() && closed(buf_.front())) {
      pair_front(out);
    }
    return out;
  }

  // At the end of the stream: the pairs of every single still held.
  std::vector<Pair> flush() {
    std::vector<Pair> out;
    while (!buf_.empty()) {
      pair_front(out);
    }
    return out;
  }

 private:
  // Keeps the buffer in (time, crystal) order: a single is in time order already, but may tie.
  void insert(const Single& s) {
    buf_.push_back(s);
    for (std::size_t i = buf_.size() - 1; i > 0 && buf_[i - 1].time == s.time && s.crystal < buf_[i - 1].crystal;
         --i) {
#if EX_MUTANT == 1
      if (i == batch_start_) {
        break;
      }
#endif
      std::swap(buf_[i - 1], buf_[i]);
    }
  }

  // A window is closed when a later single is past its end: nothing can join it any more.
  [[nodiscard]] bool closed(const Single& opener) const {
#if EX_MUTANT == 2
    (void)opener;
    return true;
#else
    return buf_.back().time - opener.time > window_;
#endif
  }

  void pair_front(std::vector<Pair>& out) {
    const Single opener = buf_.front();
    std::size_t partner = 0;
    for (std::size_t i = 1; i < buf_.size() && buf_[i].time - opener.time <= window_; ++i) {
      partner = i;
#if EX_MUTANT != 5
      break;
#endif
    }
    if (partner != 0) {
      out.push_back({opener, buf_[partner]});
      buf_.erase(buf_.begin() + static_cast<std::ptrdiff_t>(partner));
    }
    buf_.erase(buf_.begin());
  }

  std::int64_t window_;
  std::vector<Single> buf_;
  std::size_t batch_start_ = 0;
};

inline std::vector<Pair> run(std::span<const Single> singles, std::size_t batch_size, std::int64_t window) {
  Pairer pairer{window};
  std::vector<Pair> out;
  for (const auto& b : batches(singles, batch_size)) {
    const auto pairs = pairer.push(b);
    out.insert(out.end(), pairs.begin(), pairs.end());
  }
  const auto rest = pairer.flush();
  out.insert(out.end(), rest.begin(), rest.end());
  return out;
}

}  // namespace ex19
