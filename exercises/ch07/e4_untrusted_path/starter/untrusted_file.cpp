// SPDX-License-Identifier: MIT
#include "untrusted_file.hpp"

#include <fstream>
#include <sstream>

namespace ex74 {

// TODO: this is how most code reads a file. Make it safe for a name chosen by
// someone else: see the README for what the tests do to it.
minidaq::Expected<std::string, std::string> read_untrusted_file(const std::string& path, std::size_t max_bytes) {
  (void)max_bytes;
  std::ifstream in{path};
  if (!in) {
    return minidaq::Unexpected{"cannot open \"" + path + "\""};
  }
  std::stringstream ss;
  ss << in.rdbuf();
  return ss.str();
}

}  // namespace ex74
