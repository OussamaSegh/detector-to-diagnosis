// Exercise F1.1, solution: a file handle that owns its FILE* (RAII).
#pragma once

#include <atomic>
#include <cstdio>
#include <optional>
#include <string>
#include <string_view>
#include <utility>

namespace ex {

// [snippet:file]
class File {
 public:
  // The only way to get a File: it is open or there is none (no "half-built" object).
  static std::optional<File> open(const std::string& path, const char* mode) {
    std::FILE* f = std::fopen(path.c_str(), mode);
    if (f == nullptr) return std::nullopt;
    return File{f};
  }

  ~File() { close(); }

  File(const File&) = delete;  // two owners would close the same FILE* twice
  File& operator=(const File&) = delete;

  File(File&& other) noexcept : f_{std::exchange(other.f_, nullptr)} {}
  File& operator=(File&& other) noexcept {
    if (this != &other) {
      close();  // release what we own before taking the other's
      f_ = std::exchange(other.f_, nullptr);
    }
    return *this;
  }

  void close() noexcept {
    if (f_ != nullptr) {
      std::fclose(f_);
      f_ = nullptr;
      open_files().fetch_sub(1, std::memory_order_relaxed);
    }
  }
  // [/snippet:file]

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
    if (std::ferror(f_) != 0) return std::nullopt;
    return out;
  }

  // How many files are open through File right now (for the tests).
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
