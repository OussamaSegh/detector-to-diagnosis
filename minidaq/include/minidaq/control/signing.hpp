// SPDX-License-Identifier: MIT
// MiniDAQ - Ed25519 signatures and SHA-256 digests (Chapter 25, ADR 0020; release 1.3.0, ADR 0034).
//
// One place for what three parts of MiniDAQ need: the update tool verifies a bundle's manifest
// (Chapter 25), the server signs a run's record (threat T-27) and verifies a calibration table
// (threat T-54). A public key is a PEM file; a directory of them is a trust store, one *.pem per
// key, so that a key can be added before the old one is retired. A private key is a PEM file
// that only the program that signs can read; it never reaches the repository.
#pragma once

#include <array>
#include <cstddef>
#include <filesystem>
#include <memory>
#include <span>
#include <string>
#include <string_view>

#include "minidaq/core/expected.hpp"

namespace minidaq::signing {

// Whether `signature` is an Ed25519 signature of `message` by one of the public keys in keys_dir
// (*.pem). Returns the file name of the key that verified it.
[[nodiscard]] Expected<std::string, std::string> verify(std::string_view message,
                                                        std::string_view signature,
                                                        const std::filesystem::path& keys_dir);

// An Ed25519 private key, read once from a PEM file.
class SigningKey {
 public:
  [[nodiscard]] static Expected<SigningKey, std::string> load(const std::filesystem::path& pem);
  // The 64-byte signature of `message`.
  [[nodiscard]] Expected<std::string, std::string> sign(std::string_view message) const;
  // The SHA-256 of the raw public key, in hex: names the key in a record without revealing it.
  [[nodiscard]] const std::string& key_id() const noexcept { return key_id_; }

 private:
  struct Impl;
  explicit SigningKey(std::shared_ptr<const Impl> impl, std::string key_id);
  std::shared_ptr<const Impl> impl_;
  std::string key_id_;
};

// SHA-256 over bytes given in pieces.
class Sha256 {
 public:
  Sha256();
  void update(std::span<const std::byte> data);
  // The digest in lowercase hex; the object starts again afterwards.
  [[nodiscard]] std::string hex_digest();

 private:
  struct Ctx;
  struct CtxFree {
    void operator()(Ctx* c) const noexcept;
  };
  std::unique_ptr<Ctx, CtxFree> ctx_;
};

}  // namespace minidaq::signing
