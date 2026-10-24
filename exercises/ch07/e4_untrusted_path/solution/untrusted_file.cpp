// SPDX-License-Identifier: MIT
#include "untrusted_file.hpp"

#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

#include <cerrno>
#include <system_error>

namespace ex74 {
namespace {

// Closes the descriptor on every return path.
class Fd {
 public:
  explicit Fd(int fd) noexcept : fd_{fd} {}
  ~Fd() {
    if (fd_ >= 0) {
      (void)::close(fd_);  // read-only: nothing is lost if close fails
    }
  }
  Fd(const Fd&) = delete;
  Fd& operator=(const Fd&) = delete;
  Fd(Fd&&) = delete;
  Fd& operator=(Fd&&) = delete;
  [[nodiscard]] int get() const noexcept { return fd_; }

 private:
  int fd_;
};

}  // namespace

// [snippet:read]
minidaq::Expected<std::string, std::string> read_untrusted_file(const std::string& path, std::size_t max_bytes) {
  const auto fail = [&](const std::string& why) {
    return minidaq::Unexpected{"\"" + path + "\": " + why};
  };
  // O_NOFOLLOW: a symbolic link as the last component fails with ELOOP.
  // O_NONBLOCK: opening a FIFO without a writer returns at once.
  const Fd fd{::open(path.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK)};
  if (fd.get() < 0) {
    return fail(errno == ELOOP ? "is a symbolic link" : std::system_category().message(errno));
  }
  // From here on, every check is on the open file, not on the name: the name
  // may point somewhere else by now, the descriptor cannot.
  struct stat st {};
  if (::fstat(fd.get(), &st) != 0) {
    return fail(std::system_category().message(errno));
  }
  if (!S_ISREG(st.st_mode)) {
    return fail("is not a regular file");
  }
  if ((st.st_mode & S_IWOTH) != 0) {
    return fail("is writable by every user");
  }
  if (static_cast<std::size_t>(st.st_size) > max_bytes) {
    return fail("is larger than " + std::to_string(max_bytes) + " bytes");
  }
  // The size can change while we read: read at most max_bytes + 1 and look.
  std::string data(max_bytes + 1, '\0');
  std::size_t n = 0;
  while (n < data.size()) {
    const ssize_t r = ::read(fd.get(), data.data() + n, data.size() - n);
    if (r > 0) {
      n += static_cast<std::size_t>(r);
    } else if (r == 0) {
      break;
    } else if (errno != EINTR) {
      return fail(std::system_category().message(errno));
    }
  }
  if (n > max_bytes) {
    return fail("grew beyond " + std::to_string(max_bytes) + " bytes while being read");
  }
  data.resize(n);
  return data;
}
// [/snippet:read]

}  // namespace ex74
