// SPDX-License-Identifier: MIT
// Exercise 25.4: check an unpacked update against its manifest before anything runs from it.
#pragma once

#include <filesystem>
#include <string>
#include <vector>

namespace tree {

// Checks the directory `root` against `root/MANIFEST.sha256`, whose lines are written as
// `sha256sum` writes them: 64 lowercase hex digits, two spaces, a path relative to `root` with
// '/' between its components. Returns every problem as "KIND: WHAT", sorted; empty when the tree
// holds exactly the listed files with their digests. The kinds:
//   "missing: P"             P is listed and not there
//   "mismatch: P"            P is there and its SHA-256 differs
//   "unlisted: P"            P is a regular file in the tree and not listed
//   "not a regular file: P"  P is anything but a regular file or a directory (a symbolic link,
//                            a FIFO, a device), listed or not; links are never followed
//   "duplicate: P"           P is listed more than once
//   "outside the tree: P"    P is listed and is absolute, empty, or has an empty, "." or ".."
//                            component
//   "bad line: N"            line N (from 1) is not a digest, two spaces and a path
// MANIFEST.sha256 itself is not listed and not reported. Without it: {"missing: MANIFEST.sha256"}.
[[nodiscard]] std::vector<std::string> verify(const std::filesystem::path& root);

// The SHA-256 of a file as 64 lowercase hex digits; empty when it cannot be read. Given.
[[nodiscard]] std::string sha256_of(const std::filesystem::path& file);

}  // namespace tree
