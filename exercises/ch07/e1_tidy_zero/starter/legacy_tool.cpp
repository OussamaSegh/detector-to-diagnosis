// SPDX-License-Identifier: MIT
#include "legacy_tool.hpp"

#include <cerrno>
#include <cstdlib>
#include <cstring>

namespace ex71 {

bool parse_options(const std::vector<std::string>& args, Options& o) {
  for (std::size_t i = 0; i + 1 < args.size(); i += 2) {
    const char* v = args[i + 1].c_str();
    if (args[i] == "--port") {
      o.port = static_cast<std::uint16_t>(std::atoi(v));
    } else if (args[i] == "--rate") {
      o.rate_hz = std::atof(v);
    } else if (args[i] == "--repeat") {
      o.repeat = std::atoi(v);
    } else {
      return false;
    }
  }
  return true;
}

RecordFile::RecordFile(const std::string& path) {
  f_ = std::fopen(path.c_str(), "w");
}

RecordFile::~RecordFile() {
  if (f_ != nullptr) {
    std::fclose(f_);
  }
}

bool RecordFile::write(const std::string& record) {
  int n;
  if ((n = std::fputs(record.c_str(), f_)) < 0) {
    return false;
  }
  std::fputc('\n', f_);
  return true;
}

bool RecordFile::close() {
  std::fclose(f_);
  f_ = nullptr;
  return true;
}

std::string last_error() { return std::strerror(errno); }

}  // namespace ex71
