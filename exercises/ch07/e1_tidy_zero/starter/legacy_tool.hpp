// SPDX-License-Identifier: MIT
// Exercise 7.1: a small piece of "legacy" code, the kind every project has.
// It works on the happy path. clang-tidy with MiniDAQ's .clang-tidy reports a
// dozen findings in it, and some of them are real bugs: find out which.
#pragma once

#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

namespace ex71 {

struct Options {
  std::uint16_t port = 7700;
  double rate_hz = 1e6;
  int repeat = 1;
};

// Parses "--port N", "--rate HZ", "--repeat N". Returns false on bad input.
bool parse_options(const std::vector<std::string>& args, Options& o);

// Writes records, one per line, to a file.
class RecordFile {
 public:
  explicit RecordFile(const std::string& path);
  ~RecordFile();
  RecordFile(const RecordFile&) = delete;
  RecordFile& operator=(const RecordFile&) = delete;

  bool is_open() const { return f_ != nullptr; }
  // Returns false if the record was not written completely.
  bool write(const std::string& record);
  // Flushes and closes; returns false if anything written was lost.
  bool close();

 private:
  std::FILE* f_;
};

// Text for the current errno, for messages.
std::string last_error();

}  // namespace ex71
