// SPDX-License-Identifier: MIT
#include "minidaq/control/signing.hpp"

#include <openssl/evp.h>
#include <openssl/pem.h>

#include <algorithm>
#include <cstdio>
#include <memory>
#include <utility>
#include <vector>

namespace minidaq::signing {

namespace fs = std::filesystem;

namespace {

struct PkeyFree {
  void operator()(EVP_PKEY* k) const { EVP_PKEY_free(k); }
};
struct MdCtxFree {
  void operator()(EVP_MD_CTX* c) const { EVP_MD_CTX_free(c); }
};
struct FileClose {
  void operator()(std::FILE* f) const {
    (void)std::fclose(f);  // NOLINT(cppcoreguidelines-owning-memory): a FILE from fopen
  }
};

std::string to_hex(std::span<const unsigned char> bytes) {
  static constexpr std::string_view hex = "0123456789abcdef";
  std::string s;
  s.reserve(bytes.size() * 2);
  for (const unsigned char b : bytes) {
    s += hex[b >> 4U];
    s += hex[b & 0xFU];
  }
  return s;
}

// OpenSSL takes bytes.
// NOLINTBEGIN(cppcoreguidelines-pro-type-reinterpret-cast)
const unsigned char* bytes_of(std::string_view s) {
  return reinterpret_cast<const unsigned char*>(s.data());
}
// NOLINTEND(cppcoreguidelines-pro-type-reinterpret-cast)

}  // namespace

// [snippet:verify]
Expected<std::string, std::string> verify(std::string_view message, std::string_view signature,
                                          const fs::path& keys_dir) {
  std::error_code ec;
  std::vector<fs::path> keys;
  for (const auto& e : fs::directory_iterator{keys_dir, ec}) {
    if (e.path().extension() == ".pem" && e.is_regular_file()) {
      keys.push_back(e.path());
    }
  }
  if (ec || keys.empty()) {
    return Unexpected{"no public keys (*.pem) in " + keys_dir.string()};
  }
  std::ranges::sort(keys);
  for (const auto& path : keys) {
    const std::unique_ptr<std::FILE, FileClose> f{std::fopen(path.c_str(), "rb")};
    if (!f) {
      continue;
    }
    const std::unique_ptr<EVP_PKEY, PkeyFree> key{
        PEM_read_PUBKEY(f.get(), nullptr, nullptr, nullptr)};
    if (!key || EVP_PKEY_get_id(key.get()) != EVP_PKEY_ED25519) {
      continue;  // not a public key, or not Ed25519: it vouches for nothing
    }
    const std::unique_ptr<EVP_MD_CTX, MdCtxFree> ctx{EVP_MD_CTX_new()};
    // Ed25519 hashes the message itself: no digest is named, and the message goes in one call.
    if (ctx && EVP_DigestVerifyInit(ctx.get(), nullptr, nullptr, nullptr, key.get()) == 1 &&
        EVP_DigestVerify(ctx.get(), bytes_of(signature), signature.size(), bytes_of(message),
                         message.size()) == 1) {
      return path.filename().string();
    }
  }
  return Unexpected{"the signature does not verify with any key in " + keys_dir.string()};
}
// [/snippet:verify]

struct SigningKey::Impl {
  std::unique_ptr<EVP_PKEY, PkeyFree> key;
};

SigningKey::SigningKey(std::shared_ptr<const Impl> impl, std::string key_id)
    : impl_{std::move(impl)}, key_id_{std::move(key_id)} {}

Expected<SigningKey, std::string> SigningKey::load(const fs::path& pem) {
  const std::unique_ptr<std::FILE, FileClose> f{std::fopen(pem.c_str(), "rb")};
  if (!f) {
    return Unexpected{"cannot open " + pem.string()};
  }
  auto impl = std::make_shared<Impl>();
  impl->key.reset(PEM_read_PrivateKey(f.get(), nullptr, nullptr, nullptr));
  if (!impl->key || EVP_PKEY_get_id(impl->key.get()) != EVP_PKEY_ED25519) {
    return Unexpected{pem.string() + " is not an Ed25519 private key in PEM form"};
  }
  std::array<unsigned char, 32> pub{};
  std::size_t len = pub.size();
  if (EVP_PKEY_get_raw_public_key(impl->key.get(), pub.data(), &len) != 1 || len != pub.size()) {
    return Unexpected{"cannot read the public half of " + pem.string()};
  }
  std::array<unsigned char, EVP_MAX_MD_SIZE> md{};
  unsigned md_len = 0;
  if (EVP_Digest(pub.data(), pub.size(), md.data(), &md_len, EVP_sha256(), nullptr) != 1) {
    return Unexpected{std::string{"SHA-256 is not available"}};
  }
  return SigningKey{std::move(impl), to_hex(std::span(md.data(), md_len))};
}

Expected<std::string, std::string> SigningKey::sign(std::string_view message) const {
  const std::unique_ptr<EVP_MD_CTX, MdCtxFree> ctx{EVP_MD_CTX_new()};
  std::string sig(64, '\0');
  std::size_t len = sig.size();
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast): OpenSSL writes bytes
  auto* out = reinterpret_cast<unsigned char*>(sig.data());
  if (!ctx || EVP_DigestSignInit(ctx.get(), nullptr, nullptr, nullptr, impl_->key.get()) != 1 ||
      EVP_DigestSign(ctx.get(), out, &len, bytes_of(message), message.size()) != 1 ||
      len != sig.size()) {
    return Unexpected{std::string{"Ed25519 signing failed"}};
  }
  return sig;
}

struct Sha256::Ctx {
  EVP_MD_CTX* md = nullptr;
};

void Sha256::CtxFree::operator()(Ctx* c) const noexcept {
  EVP_MD_CTX_free(c->md);
  delete c;  // NOLINT(cppcoreguidelines-owning-memory): owned by the unique_ptr
}

Sha256::Sha256() : ctx_{new Ctx{EVP_MD_CTX_new()}} {  // NOLINT(cppcoreguidelines-owning-memory)
  (void)EVP_DigestInit_ex(ctx_->md, EVP_sha256(), nullptr);
}

void Sha256::update(std::span<const std::byte> data) {
  (void)EVP_DigestUpdate(ctx_->md, data.data(), data.size());
}

std::string Sha256::hex_digest() {
  std::array<unsigned char, EVP_MAX_MD_SIZE> md{};
  unsigned len = 0;
  (void)EVP_DigestFinal_ex(ctx_->md, md.data(), &len);
  (void)EVP_DigestInit_ex(ctx_->md, EVP_sha256(), nullptr);
  return to_hex(std::span(md.data(), len));
}

}  // namespace minidaq::signing
