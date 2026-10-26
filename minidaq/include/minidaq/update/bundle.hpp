// SPDX-License-Identifier: MIT
// MiniDAQ - an update bundle and how it is trusted (Chapter 25, ADR 0020).
//
// A bundle is a directory with three files:
//
//   update.json       the manifest: product, version, commit, platform, archive name, size, SHA-256
//   update.json.sig   an Ed25519 signature of update.json's exact bytes (64 bytes, raw)
//   <archive>.tar.gz  the programs and data of one version, with MANIFEST.sha256 inside
//
// Trust goes in one direction. The signature is checked first, with the public keys installed
// on the acquisition PC (one *.pem file each, so that a key can be added before the old one is
// retired); only then is the manifest parsed, and only through the manifest is the archive
// trusted, by its size and SHA-256; and only through the archive's MANIFEST.sha256 is each
// extracted file trusted. Nothing in the bundle is read before what vouches for it has been
// verified. Signing happens on the release side (tools/make_update.py) with a private key that
// never reaches the repository or the acquisition PC.
#pragma once

#include <compare>
#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <string_view>

#include "minidaq/core/expected.hpp"

namespace minidaq::update {

// MAJOR.MINOR.PATCH with an optional pre-release ("0.5.0-rc.1"), as in VERSION. A pre-release
// is older than its release; two pre-releases compare as strings, enough for "-rc.N" with N < 10
// (assumption: confirm with team if releases need more).
struct Version {
  unsigned major = 0;
  unsigned minor = 0;
  unsigned patch = 0;
  std::string pre;
  [[nodiscard]] static std::optional<Version> parse(std::string_view text);
  [[nodiscard]] std::string str() const;
  friend std::strong_ordering operator<=>(const Version& a, const Version& b);
  friend bool operator==(const Version& a, const Version& b) = default;
};

// [snippet:manifest]
inline constexpr std::string_view manifest_format = "minidaq-update 1";

struct Manifest {
  std::string product;  // "minidaq"
  Version version;
  std::string commit;    // the source it was built from
  std::string platform;  // the platform definition it was built and verified for
  std::string archive;   // a file name in the bundle's directory, *.tar.gz
  std::uint64_t size = 0;
  std::string sha256;  // of the archive, 64 lowercase hex digits
};
// [/snippet:manifest]

// Parses a manifest's text; every field is required and checked.
[[nodiscard]] Expected<Manifest, std::string> parse_manifest(std::string_view text);

// Whether `signature` is an Ed25519 signature of `message` by one of the public keys in
// keys_dir (*.pem). Returns the file name of the key that verified it.
[[nodiscard]] Expected<std::string, std::string> verify_signature(
    std::string_view message, std::string_view signature, const std::filesystem::path& keys_dir);

// The verified manifest of the bundle in `dir`, and the key that signed it.
struct SignedManifest {
  Manifest manifest;
  std::string key;
};
[[nodiscard]] Expected<SignedManifest, std::string> read_signed_manifest(
    const std::filesystem::path& dir, const std::filesystem::path& keys_dir);

// SHA-256 of a file, in lowercase hex, and its size.
struct Digest {
  std::string sha256;
  std::uint64_t size = 0;
};
[[nodiscard]] Expected<Digest, std::string> digest_file(const std::filesystem::path& file);

}  // namespace minidaq::update
