// SPDX-License-Identifier: MIT
#include "minidaq/control/file_ops.hpp"

#include <fcntl.h>
#include <unistd.h>

#include <cerrno>
#include <cstdio>
#include <system_error>

namespace minidaq::control {

namespace {

class PosixFileOps final : public FileOps {
 public:
  Expected<int, int> create(const std::string& path) override {
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg): open(2) is variadic
    const int fd = ::open(path.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0644);
    if (fd < 0) {
      return Unexpected{errno};
    }
    return fd;
  }

  Expected<std::size_t, int> write(int handle, std::span<const std::byte> data) override {
    while (true) {
      const ::ssize_t n = ::write(handle, data.data(), data.size());
      if (n >= 0) {
        return static_cast<std::size_t>(n);
      }
      if (errno != EINTR) {
        return Unexpected{errno};
      }
    }
  }

  int sync(int handle) override { return ::fsync(handle) == 0 ? 0 : errno; }

  int close(int handle) override { return ::close(handle) == 0 ? 0 : errno; }

  int rename_no_replace(const std::string& from, const std::string& to) override {
#ifdef RENAME_NOREPLACE
    if (::renameat2(AT_FDCWD, from.c_str(), AT_FDCWD, to.c_str(), RENAME_NOREPLACE) == 0) {
      return 0;
    }
    if (errno != EINVAL && errno != ENOSYS) {
      return errno;
    }
#endif
    // link(2) fails with EEXIST rather than replace, and is atomic; then the old name goes.
    if (::link(from.c_str(), to.c_str()) != 0) {
      return errno;
    }
    return ::unlink(from.c_str()) == 0 ? 0 : errno;
  }

  int sync_directory(const std::string& dir) override {
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg): open(2) is variadic
    const int fd = ::open(dir.c_str(), O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (fd < 0) {
      return errno;
    }
    const int r = ::fsync(fd) == 0 ? 0 : errno;
    ::close(fd);
    return r;
  }
};

}  // namespace

std::unique_ptr<FileOps> make_posix_file_ops() { return std::make_unique<PosixFileOps>(); }

std::string errno_message(int err) { return std::system_category().message(err); }

}  // namespace minidaq::control
