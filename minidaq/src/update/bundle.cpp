// SPDX-License-Identifier: MIT
#include "minidaq/update/bundle.hpp"

#include <openssl/evp.h>

#include <algorithm>
#include <array>
#include <cstdio>
#include <fstream>
#include <memory>
#include <nlohmann/json.hpp>
#include <sstream>
#include <vector>

#include "minidaq/control/signing.hpp"
#include "minidaq/core/parse_number.hpp"

namespace minidaq::update {

namespace fs = std::filesystem;

std::optional<Version> Version::parse(std::string_view text) {
  Version v;
  const auto dash = text.find('-');
  const std::string_view core = text.substr(0, dash);
  if (dash != std::string_view::npos) {
    v.pre = std::string{text.substr(dash + 1)};
    if (v.pre.empty()) {
      return std::nullopt;
    }
  }
  std::array<unsigned*, 3> parts{&v.major, &v.minor, &v.patch};
  std::size_t from = 0;
  for (std::size_t i = 0; i < parts.size(); ++i) {
    const auto dot = i + 1 < parts.size() ? core.find('.', from) : core.size();
    if (dot == std::string_view::npos ||
        !parse_into<unsigned>(core.substr(from, dot - from), *parts[i], 0, 99'999)) {
      return std::nullopt;
    }
    from = dot + 1;
  }
  return v;
}

std::string Version::str() const {
  const std::string s =
      std::to_string(major) + "." + std::to_string(minor) + "." + std::to_string(patch);
  return pre.empty() ? s : s + "-" + pre;
}

std::strong_ordering operator<=>(const Version& a, const Version& b) {
  if (auto c = std::tie(a.major, a.minor, a.patch) <=> std::tie(b.major, b.minor, b.patch);
      c != 0) {
    return c;
  }
  if (a.pre.empty() != b.pre.empty()) {
    return a.pre.empty() ? std::strong_ordering::greater : std::strong_ordering::less;
  }
  return a.pre <=> b.pre;
}

namespace {

bool is_hex64(const std::string& s) {
  return s.size() == 64 && std::ranges::all_of(s, [](char c) {
           return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
         });
}

std::string read_file(const fs::path& p, bool& ok) {
  const std::ifstream in{p, std::ios::binary};
  std::ostringstream text;
  text << in.rdbuf();
  ok = static_cast<bool>(in);
  return text.str();
}

struct MdCtxFree {
  void operator()(EVP_MD_CTX* c) const { EVP_MD_CTX_free(c); }
};
struct FileClose {
  void operator()(std::FILE* f) const {
    (void)std::fclose(f);  // NOLINT(cppcoreguidelines-owning-memory): a FILE from fopen
  }
};

}  // namespace

Expected<Manifest, std::string> parse_manifest(std::string_view text) {
  const auto j = nlohmann::json::parse(text, nullptr, false);
  if (!j.is_object()) {
    return Unexpected{std::string{"the manifest is not a JSON object"}};
  }
  const auto str = [&j](const char* key) -> std::optional<std::string> {
    if (!j.contains(key) || !j[key].is_string()) {
      return std::nullopt;
    }
    return j[key].get<std::string>();
  };
  for (const char* key :
       {"format", "product", "version", "commit", "platform", "archive", "sha256"}) {
    if (!str(key).has_value()) {
      return Unexpected{std::string{"the manifest has no string \""} + key + "\""};
    }
  }
  // Every key was checked above; the values are read once into plain strings.
  const auto get = [&j](const char* key) { return j[key].get<std::string>(); };
  const std::string format = get("format");
  if (format != manifest_format) {
    return Unexpected{"the manifest's format is \"" + format + "\", not \"" +
                      std::string{manifest_format} + "\""};
  }
  if (!j.contains("size") || !j["size"].is_number_unsigned()) {
    return Unexpected{std::string{"the manifest has no size in bytes"}};
  }
  Manifest m;
  m.product = get("product");
  m.commit = get("commit");
  m.platform = get("platform");
  m.archive = get("archive");
  m.sha256 = get("sha256");
  m.size = j["size"].get<std::uint64_t>();
  const std::string version = get("version");
  const auto v = Version::parse(version);
  if (!v) {
    return Unexpected{"the manifest's version \"" + version + "\" is not MAJOR.MINOR.PATCH"};
  }
  m.version = *v;
  // A plain file name next to the manifest: nothing the manifest names can be elsewhere.
  if (m.archive.empty() || m.archive.find('/') != std::string::npos || m.archive.front() == '.' ||
      !m.archive.ends_with(".tar.gz")) {
    return Unexpected{"the manifest's archive \"" + m.archive +
                      "\" is not a file name ending in .tar.gz"};
  }
  if (!is_hex64(m.sha256)) {
    return Unexpected{std::string{"the manifest's sha256 is not 64 lowercase hex digits"}};
  }
  return m;
}

// The verification itself is shared with the server (minidaq/control/signing.hpp, ADR 0034).
Expected<std::string, std::string> verify_signature(std::string_view message,
                                                    std::string_view signature,
                                                    const fs::path& keys_dir) {
  return signing::verify(message, signature, keys_dir);
}

Expected<SignedManifest, std::string> read_signed_manifest(const fs::path& dir,
                                                           const fs::path& keys_dir) {
  bool ok = false;
  const std::string text = read_file(dir / "update.json", ok);
  if (!ok) {
    return Unexpected{"cannot read " + (dir / "update.json").string()};
  }
  const std::string sig = read_file(dir / "update.json.sig", ok);
  if (!ok) {
    return Unexpected{"cannot read " + (dir / "update.json.sig").string()};
  }
  auto key = verify_signature(text, sig, keys_dir);
  if (!key) {
    return Unexpected{"update.json: " + key.error()};
  }
  auto m = parse_manifest(text);  // only now: an unsigned manifest is never parsed
  if (!m) {
    return Unexpected{"update.json: " + m.error()};
  }
  return SignedManifest{std::move(*m), std::move(*key)};
}

Expected<Digest, std::string> digest_file(const fs::path& file) {
  const std::unique_ptr<std::FILE, FileClose> f{std::fopen(file.c_str(), "rb")};
  if (!f) {
    return Unexpected{"cannot open " + file.string()};
  }
  const std::unique_ptr<EVP_MD_CTX, MdCtxFree> ctx{EVP_MD_CTX_new()};
  if (!ctx || EVP_DigestInit_ex(ctx.get(), EVP_sha256(), nullptr) != 1) {
    return Unexpected{std::string{"SHA-256 is not available"}};
  }
  Digest d;
  std::vector<unsigned char> buf(1U << 16U);
  std::size_t n = 0;
  while ((n = std::fread(buf.data(), 1, buf.size(), f.get())) > 0) {
    (void)EVP_DigestUpdate(ctx.get(), buf.data(), n);
    d.size += n;
  }
  if (std::ferror(f.get()) != 0) {
    return Unexpected{"cannot read " + file.string()};
  }
  std::array<unsigned char, EVP_MAX_MD_SIZE> md{};
  unsigned len = 0;
  (void)EVP_DigestFinal_ex(ctx.get(), md.data(), &len);
  static constexpr std::string_view hex = "0123456789abcdef";
  for (unsigned i = 0; i < len; ++i) {
    d.sha256 += hex[md[i] >> 4U];
    d.sha256 += hex[md[i] & 0xFU];
  }
  return d;
}

}  // namespace minidaq::update
