// SPDX-License-Identifier: MIT
#include "verify_tree.hpp"

#include <algorithm>
#include <fstream>
#include <map>
#include <set>
#include <string_view>
#include <system_error>

namespace tree {

namespace fs = std::filesystem;

namespace {

bool is_digest(std::string_view s) {
  return s.size() == 64 && std::ranges::all_of(s, [](char c) {
           return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
         });
}

// A relative path whose every component is a name: nothing it names can be outside `root`.
bool inside(std::string_view p) {
  if (p.empty() || p.front() == '/') {
    return false;
  }
  while (true) {
    const auto slash = p.find('/');
    const std::string_view part = p.substr(0, slash);
    if (part.empty() || part == "." || part == "..") {
      return false;
    }
    if (slash == std::string_view::npos) {
      return true;
    }
    p.remove_prefix(slash + 1);
  }
}

}  // namespace

std::vector<std::string> verify(const fs::path& root) {
  std::vector<std::string> problems;
  std::ifstream in{root / "MANIFEST.sha256"};
  if (!in) {
    return {"missing: MANIFEST.sha256"};
  }
  std::map<std::string, std::string> listed;  // path -> digest
  std::string line;
  for (int n = 1; std::getline(in, line); ++n) {
    if (line.size() < 67 || !is_digest(line.substr(0, 64)) || line.substr(64, 2) != "  ") {
      problems.push_back("bad line: " + std::to_string(n));
      continue;
    }
    const std::string path = line.substr(66);
    if (!inside(path)) {
      problems.push_back("outside the tree: " + path);
    } else if (!listed.emplace(path, line.substr(0, 64)).second) {
      problems.push_back("duplicate: " + path);
    }
  }

  // What is there, without following a single link.
  std::set<std::string> present;
  std::error_code ec;
  for (auto it = fs::recursive_directory_iterator{root, ec}; !ec && it != fs::end(it);
       it.increment(ec)) {
    const auto rel = it->path().lexically_relative(root).generic_string();
    const auto type = it->symlink_status(ec).type();
    if (type == fs::file_type::directory) {
      continue;
    }
    if (type != fs::file_type::regular) {
      problems.push_back("not a regular file: " + rel);
    } else if (rel != "MANIFEST.sha256") {
      present.insert(rel);
    }
  }

  for (const auto& [path, digest] : listed) {
    const auto type = fs::symlink_status(root / path, ec).type();
    if (type == fs::file_type::not_found) {
      problems.push_back("missing: " + path);
    } else if (present.contains(path) && sha256_of(root / path) != digest) {
      problems.push_back("mismatch: " + path);
    }  // anything else that is there was reported as not a regular file above
  }
  for (const auto& path : present) {
    if (!listed.contains(path)) {
      problems.push_back("unlisted: " + path);
    }
  }
  std::ranges::sort(problems);
  problems.erase(std::ranges::unique(problems).begin(), problems.end());
  return problems;
}

}  // namespace tree
