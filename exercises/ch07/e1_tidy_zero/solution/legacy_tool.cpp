// SPDX-License-Identifier: MIT
#include "legacy_tool.hpp"

#include <cerrno>
#include <system_error>

#include "minidaq/core/parse_number.hpp"

namespace ex71 {

bool parse_options(const std::vector<std::string>& args, Options& o) {
  if (args.size() % 2 != 0) {
    return false;  // an option without its value
  }
  Options next = o;  // all or nothing
  for (std::size_t i = 0; i < args.size(); i += 2) {
    const std::string& v = args[i + 1];
    bool ok = false;
    if (args[i] == "--port") {
      ok = minidaq::parse_into<std::uint16_t>(v, next.port, 1, 65535);
    } else if (args[i] == "--rate") {
      ok = minidaq::parse_into(v, next.rate_hz, 1e-3, 1e9);
    } else if (args[i] == "--repeat") {
      ok = minidaq::parse_into(v, next.repeat, 1, 1'000'000);
    }
    if (!ok) {
      return false;
    }
  }
  o = next;
  return true;
}

RecordFile::RecordFile(const std::string& path)
    : f_{std::fopen(path.c_str(), "w")} {}  // NOLINT(cppcoreguidelines-owning-memory): owned by f_

bool RecordFile::write(const std::string& record) {
  if (!f_) {
    return false;
  }
  const bool ok = std::fputs(record.c_str(), f_.get()) >= 0 && std::fputc('\n', f_.get()) != EOF;
  failed_ = failed_ || !ok;
  return ok;
}

bool RecordFile::close() {
  if (!f_) {
    return false;
  }
  // fclose flushes; a full disk often shows only here. Check both, then release.
  const bool flushed = std::fflush(f_.get()) == 0;
  const bool closed = std::fclose(f_.release()) == 0;
  return flushed && closed && !failed_;
}

std::string last_error() { return std::system_category().message(errno); }

}  // namespace ex71
