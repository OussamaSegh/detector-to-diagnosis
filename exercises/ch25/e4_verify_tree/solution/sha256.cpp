// SPDX-License-Identifier: MIT
// Given: the digest, computed by MiniDAQ's updater library (OpenSSL's SHA-256).
#include "minidaq/update/bundle.hpp"
#include "verify_tree.hpp"

namespace tree {

std::string sha256_of(const std::filesystem::path& file) {
  const auto d = minidaq::update::digest_file(file);
  return d ? d->sha256 : std::string{};
}

}  // namespace tree
