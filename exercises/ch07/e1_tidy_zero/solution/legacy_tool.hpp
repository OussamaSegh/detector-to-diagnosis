// SPDX-License-Identifier: MIT
// Exercise 7.1 solution: the legacy code with every clang-tidy finding fixed
// (none suppressed), and the bugs behind them with it.
#pragma once

#include <cstdint>
#include <cstdio>
#include <memory>
#include <string>
#include <vector>

namespace ex71 {

struct Options {
  std::uint16_t port = 7700;
  double rate_hz = 1e6;
  int repeat = 1;
};

// Parses "--port N", "--rate HZ", "--repeat N". Returns false on bad input
// and then leaves `o` unchanged.
[[nodiscard]] bool parse_options(const std::vector<std::string>& args, Options& o);

// Writes records, one per line, to a file.
class RecordFile {
 public:
  explicit RecordFile(const std::string& path);

  [[nodiscard]] bool is_open() const { return f_ != nullptr; }
  // Returns false if the record was not written completely.
  [[nodiscard]] bool write(const std::string& record);
  // Flushes and closes; returns false if anything written was lost.
  [[nodiscard]] bool close();

 private:
  struct Closer {
    // Only reached if close() was not called; close() is where errors are reported.
    void operator()(std::FILE* f) const noexcept { (void)std::fclose(f); }  // NOLINT(cppcoreguidelines-owning-memory): the owner
  };
  std::unique_ptr<std::FILE, Closer> f_;
  bool failed_ = false;
};

// Text for the current errno, for messages.
[[nodiscard]] std::string last_error();

}  // namespace ex71
