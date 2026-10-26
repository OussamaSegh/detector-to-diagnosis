// SPDX-License-Identifier: MIT
#include "verify_tree.hpp"

#include <fstream>

namespace tree {

std::vector<std::string> verify(const std::filesystem::path& root) {
  // TODO: this checks the digest of every listed file, and nothing else: not what is in the tree
  // without being listed, not links, not where a listed path points, not the lines themselves.
  std::vector<std::string> problems;
  std::ifstream in{root / "MANIFEST.sha256"};
  std::string line;
  while (std::getline(in, line)) {
    const std::string digest = line.substr(0, 64);
    const std::string path = line.substr(66);
    if (sha256_of(root / path) != digest) {
      problems.push_back("mismatch: " + path);
    }
  }
  return problems;
}

}  // namespace tree
