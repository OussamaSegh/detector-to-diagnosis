// Exercise F1.1, starter: a file handle written the "C way". It compiles and it works as long as
// every caller remembers to call close() exactly once, on every path, including exceptions.
// Turn it into an owner: the destructor closes, copies are impossible, moves transfer.
#pragma once

#include <atomic>
#include <cstdio>
#include <optional>
#include <string>
#include <string_view>

namespace ex {

class File {
 public:
  static std::optional<File> open(const std::string& path, const char* mode) {
    std::FILE* f = std::fopen(path.c_str(), mode);
    if (f == nullptr) return std::nullopt;
    return File{f};
  }

  // TODO: a destructor that closes the file.
  // TODO: delete the copy operations (two owners would close one FILE* twice).
  // TODO: move operations that leave the source empty; move assignment closes the old file.

  void close() noexcept {
    if (f_ != nullptr) {
      std::fclose(f_);
      f_ = nullptr;
      open_files().fetch_sub(1, std::memory_order_relaxed);
    }
  }

  [[nodiscard]] bool is_open() const noexcept { return f_ != nullptr; }

  bool write(std::string_view text) noexcept {
    if (f_ == nullptr) return false;
    return std::fwrite(text.data(), 1, text.size(), f_) == text.size();
  }

  [[nodiscard]] std::optional<std::string> read_all() {
    if (f_ == nullptr) return std::nullopt;
    std::string out;
    char buf[4096];
    std::size_t n = 0;
    while ((n = std::fread(buf, 1, sizeof buf, f_)) > 0) out.append(buf, n);
    return out;
  }

  static int open_count() noexcept { return open_files().load(std::memory_order_relaxed); }

 private:
  explicit File(std::FILE* f) noexcept : f_{f} {
    open_files().fetch_add(1, std::memory_order_relaxed);
  }
  static std::atomic<int>& open_files() noexcept {
    static std::atomic<int> n{0};
    return n;
  }

  std::FILE* f_ = nullptr;
};

}  // namespace ex
