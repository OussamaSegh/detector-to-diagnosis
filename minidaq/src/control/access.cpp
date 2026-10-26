// SPDX-License-Identifier: MIT
#include "minidaq/control/access.hpp"

#include <fcntl.h>
#include <openssl/crypto.h>
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <sys/stat.h>
#include <unistd.h>

#include <array>
#include <cerrno>
#include <cstdlib>
#include <string>
#include <system_error>

#include <nlohmann/json.hpp>

namespace minidaq::control {

namespace {

constexpr std::string_view prefix = "mdq_";
constexpr std::size_t secret_bytes = 32;

std::string errno_text(const std::string& what) { return what + ": " + std::system_category().message(errno); }

std::string sha256(std::string_view data) {
  std::array<unsigned char, EVP_MAX_MD_SIZE> md{};
  unsigned int len = 0;
  if (EVP_Digest(data.data(), data.size(), md.data(), &len, EVP_sha256(), nullptr) != 1) {
    return {};
  }
  return {md.begin(), md.begin() + len};
}

std::string to_hex(std::string_view bytes) {
  static constexpr std::string_view digits = "0123456789abcdef";
  std::string out;
  out.reserve(bytes.size() * 2);
  for (const char c : bytes) {
    const auto b = static_cast<unsigned char>(c);
    out += digits[b >> 4U];
    out += digits[b & 0xFU];
  }
  return out;
}

std::optional<std::string> from_hex(std::string_view hex) {
  if (hex.size() % 2 != 0) {
    return std::nullopt;
  }
  auto nibble = [](char c) -> int {
    if (c >= '0' && c <= '9') {
      return c - '0';
    }
    if (c >= 'a' && c <= 'f') {
      return c - 'a' + 10;
    }
    return -1;
  };
  std::string out;
  for (std::size_t i = 0; i < hex.size(); i += 2) {
    const int hi = nibble(hex[i]);
    const int lo = nibble(hex[i + 1]);
    if (hi < 0 || lo < 0) {
      return std::nullopt;
    }
    out += static_cast<char>((hi << 4) | lo);
  }
  return out;
}

// The file or directory may be used for a secret: ours, not a link, and not open to
// others in the ways `forbidden` names.
std::optional<std::string> unsafe(const std::filesystem::path& p, const struct stat& st, mode_t forbidden) {
  if (S_ISLNK(st.st_mode)) {
    return p.string() + " is a symbolic link";
  }
  if (st.st_uid != ::geteuid()) {
    return p.string() + " belongs to another user";
  }
  if ((st.st_mode & forbidden) != 0) {
    std::string mode;
    for (unsigned shift = 9;; shift -= 3) {  // four octal digits, as chmod writes them
      mode += static_cast<char>('0' + ((st.st_mode >> shift) & 7U));
      if (shift == 0) {
        break;
      }
    }
    return p.string() + " is accessible to other users (mode " + mode + "; use 0600 for a file, 0700 for a directory)";
  }
  return std::nullopt;
}

}  // namespace

std::string_view to_string(Role r) noexcept {
  switch (r) {
    case Role::observer:
      return "observer";
    case Role::operator_:
      return "operator";
    case Role::none:
      break;
  }
  return "none";
}

std::optional<Role> role_from_string(std::string_view s) noexcept {
  if (s == "observer") {
    return Role::observer;
  }
  if (s == "operator") {
    return Role::operator_;
  }
  return std::nullopt;
}

// [snippet:roles]
Role required_role(std::string_view cmd) noexcept {
  if (cmd == "hello" || cmd == "auth") {
    return Role::none;
  }
  if (cmd == "status" || cmd == "diagnostics") {
    return Role::observer;
  }
  return Role::operator_;  // configure, start, stop, reset, and any command added later
}
// [/snippet:roles]

Expected<TokenStore, std::string> TokenStore::load(const std::filesystem::path& path) {
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg): open(2) is variadic
  const int fd = ::open(path.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
  if (fd < 0) {
    return Unexpected{errno_text(path.string())};
  }
  struct stat st{};
  std::string text;
  std::optional<std::string> problem;
  if (::fstat(fd, &st) != 0) {
    problem = errno_text(path.string());
  } else if (!S_ISREG(st.st_mode)) {
    problem = path.string() + " is not a regular file";
  } else {
    problem = unsafe(path, st, S_IWGRP | S_IWOTH);
  }
  for (std::array<char, 4096> buf{}; !problem;) {
    const ssize_t n = ::read(fd, buf.data(), buf.size());
    if (n < 0 && errno == EINTR) {
      continue;
    }
    if (n < 0) {
      problem = errno_text(path.string());
    }
    if (n <= 0) {
      break;
    }
    text.append(buf.data(), static_cast<std::size_t>(n));
  }
  ::close(fd);
  if (problem) {
    return Unexpected{*problem};
  }
  const auto doc = nlohmann::json::parse(text, nullptr, false);
  if (!doc.is_object() || !doc.contains("tokens") || !doc["tokens"].is_array()) {
    return Unexpected{path.string() + ": expected {\"tokens\": [...]}"};
  }
  TokenStore store;
  for (const auto& t : doc["tokens"]) {
    const std::string where = path.string() + ": token " + std::to_string(store.entries_.size() + 1);
    if (!t.is_object() || !t.contains("name") || !t["name"].is_string() || !t.contains("role") ||
        !t["role"].is_string() || !t.contains("sha256") || !t["sha256"].is_string()) {
      return Unexpected{where + R"(: needs the strings "name", "role" and "sha256")"};
    }
    const auto role_found = role_from_string(t["role"].get<std::string>());
    if (!role_found) {
      return Unexpected{where + R"(: role must be "observer" or "operator")"};
    }
    const auto hash_found = from_hex(t["sha256"].get<std::string>());
    if (!hash_found || hash_found->size() != 32) {
      return Unexpected{where + ": sha256 must be 64 lowercase hex digits"};
    }
    const Role role = *role_found;
    const std::string& hash = *hash_found;
    const auto name = t["name"].get<std::string>();
    for (const auto& e : store.entries_) {
      if (e.identity.name == name || e.sha256 == hash) {
        return Unexpected{where + ": name or token used twice"};
      }
    }
    store.entries_.push_back({{name, role}, hash});
  }
  if (store.entries_.empty()) {
    return Unexpected{path.string() + ": no tokens"};
  }
  return store;
}

TokenStore TokenStore::single(std::string name, Role role, std::string_view token) {
  TokenStore store;
  store.entries_.push_back({{std::move(name), role}, sha256(token)});
  return store;
}

// [snippet:check]
std::optional<Identity> TokenStore::check(std::string_view token) const {
  const std::string h = sha256(token);
  const Entry* found = nullptr;
  for (const auto& e : entries_) {  // no early exit: every entry is compared
    if (h.size() == e.sha256.size() && CRYPTO_memcmp(h.data(), e.sha256.data(), h.size()) == 0) {
      found = &e;
    }
  }
  if (found == nullptr) {
    return std::nullopt;
  }
  return found->identity;
}
// [/snippet:check]

std::string new_token() {
  std::array<unsigned char, secret_bytes> bytes{};
  if (RAND_bytes(bytes.data(), static_cast<int>(bytes.size())) != 1) {
    return {};
  }
  const std::string raw{bytes.begin(), bytes.end()};
  OPENSSL_cleanse(bytes.data(), bytes.size());
  return std::string{prefix} + to_hex(raw);
}

std::string token_sha256_hex(std::string_view token) { return to_hex(sha256(token)); }

std::filesystem::path default_token_path(std::uint16_t port) {
  std::filesystem::path dir;
  // getenv is read before any thread starts (in main) or in tests; nothing here sets the environment.
  if (const char* d = std::getenv("MINIDAQ_RUNTIME_DIR"); d != nullptr && *d != '\0') {  // NOLINT(concurrency-mt-unsafe)
    dir = d;
  } else if (const char* x = std::getenv("XDG_RUNTIME_DIR"); x != nullptr && *x != '\0') {  // NOLINT(concurrency-mt-unsafe)
    dir = std::filesystem::path{x} / "minidaq";
  } else {
    dir = "/tmp/minidaq-" + std::to_string(::geteuid());
  }
  return dir / ("minidaq-" + std::to_string(port) + ".token");
}

Expected<std::filesystem::path, std::string> write_secret(const std::filesystem::path& path, std::string_view secret) {
  const auto dir = path.parent_path();
  if (::mkdir(dir.c_str(), 0700) != 0 && errno != EEXIST) {
    return Unexpected{errno_text(dir.string())};
  }
  struct stat st{};
  if (::lstat(dir.c_str(), &st) != 0) {
    return Unexpected{errno_text(dir.string())};
  }
  if (auto p = unsafe(dir, st, S_IRWXG | S_IRWXO)) {
    return Unexpected{*p};
  }
  if (!S_ISDIR(st.st_mode)) {
    return Unexpected{dir.string() + " is not a directory"};
  }
  // A file left by a server that crashed is ours (the directory is), so it may go.
  if (::unlink(path.c_str()) != 0 && errno != ENOENT) {
    return Unexpected{errno_text(path.string())};
  }
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg): open(2) is variadic
  const int fd = ::open(path.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
  if (fd < 0) {
    return Unexpected{errno_text(path.string())};
  }
  const std::string line = std::string{secret} + "\n";
  const ssize_t n = ::write(fd, line.data(), line.size());
  const bool ok = n == static_cast<ssize_t>(line.size());
  const int err = errno;
  ::close(fd);
  if (!ok) {
    errno = err;
    (void)::unlink(path.c_str());
    return Unexpected{errno_text(path.string())};
  }
  return path;
}

Expected<std::string, std::string> read_secret(const std::filesystem::path& path) {
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg): open(2) is variadic
  const int fd = ::open(path.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
  if (fd < 0) {
    return Unexpected{errno_text(path.string())};
  }
  struct stat st{};
  std::optional<std::string> problem;
  if (::fstat(fd, &st) != 0) {
    problem = errno_text(path.string());
  } else {
    problem = unsafe(path, st, S_IRWXG | S_IRWXO);
  }
  std::array<char, 256> buf{};
  ssize_t n = 0;
  if (!problem) {
    n = ::read(fd, buf.data(), buf.size());
    if (n < 0) {
      problem = errno_text(path.string());
    }
  }
  ::close(fd);
  if (problem) {
    return Unexpected{*problem};
  }
  std::string s{buf.data(), static_cast<std::size_t>(n)};
  while (!s.empty() && (s.back() == '\n' || s.back() == '\r' || s.back() == ' ')) {
    s.pop_back();
  }
  if (s.empty()) {
    return Unexpected{path.string() + " is empty"};
  }
  return s;
}

}  // namespace minidaq::control
