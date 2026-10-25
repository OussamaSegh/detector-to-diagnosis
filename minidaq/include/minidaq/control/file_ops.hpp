// SPDX-License-Identifier: MIT
// MiniDAQ - the file operations a durable writer needs (Chapter 12), behind
// an interface so that tests can make them fail.
//
// A disk fills up, a write returns fewer bytes than asked, fsync reports an
// I/O error. These are rare in a test run and certain over a scanner's
// lifetime, so the code that handles them must be tested, and it can be only
// if the failures can be produced on demand. Every function returns an errno
// value (0 for success) instead of throwing: these are expected outcomes.
#pragma once

#include <cstddef>
#include <memory>
#include <span>
#include <string>

#include "minidaq/core/expected.hpp"

namespace minidaq::control {

// [snippet:fileops]
class FileOps {
 public:
  virtual ~FileOps() = default;
  // Creates a new file for writing; fails (EEXIST) if it exists. Returns a handle.
  [[nodiscard]] virtual Expected<int, int> create(const std::string& path) = 0;
  // Writes some of `data`: possibly fewer bytes than asked, never zero unless data is empty.
  [[nodiscard]] virtual Expected<std::size_t, int> write(int handle, std::span<const std::byte> data) = 0;
  [[nodiscard]] virtual int sync(int handle) = 0;  // fsync: data and metadata on stable storage
  [[nodiscard]] virtual int close(int handle) = 0;
  // Renames atomically; fails (EEXIST) instead of replacing an existing file.
  [[nodiscard]] virtual int rename_no_replace(const std::string& from, const std::string& to) = 0;
  // fsync of a directory, which makes a rename or a new file in it durable.
  [[nodiscard]] virtual int sync_directory(const std::string& dir) = 0;
};
// [/snippet:fileops]

// The real thing: open(2) with O_CREAT | O_EXCL, write(2) retried on EINTR,
// fsync(2), renameat2(2) with RENAME_NOREPLACE (link(2) and unlink(2) where
// the file system does not support it).
[[nodiscard]] std::unique_ptr<FileOps> make_posix_file_ops();

// "No space left on device" and the like, for messages.
[[nodiscard]] std::string errno_message(int err);

}  // namespace minidaq::control
