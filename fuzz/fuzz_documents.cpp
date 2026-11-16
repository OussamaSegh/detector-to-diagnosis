// SPDX-License-Identifier: MIT
// Fuzz target: the JSON documents MiniDAQ reads from files that a person or another program
// writes (CAPA-0005, coding standard rule 3.4). The first byte chooses the reader; the rest of the
// input is the document's text:
//
//   0: the hardware description, config::parse_hardware_config (Chapter 22).
//   1: an update bundle's manifest, update::parse_manifest (Chapter 25).
//   2: the token file, control::TokenStore::load, from a file of mode 0600 (Chapter 17).
//   3: a signed run record, control::verify_signed_run (release 1.3.0): the text is signed with a
//      key made when the target starts, so the reader gets past the signature to the fields, as a
//      record written by a site's own key would (MDQ-PR-071). The run's directory holds one data
//      file, run-0000.mdql, of three bytes.
//   4: the update store's state, update::SlotStore::open with the text as state.json (Chapter 25).
//
// Properties besides "no crash and no exception": a refusal always says why; an accepted signed
// run names the key that signed it and lists only files that exist with their stated size.
// The private key is made in a temporary directory at start-up and never written elsewhere.
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <unistd.h>

#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <memory>
#include <string>
#include <string_view>

#include <nlohmann/json.hpp>

#include "minidaq/config/hardware_config.hpp"
#include "minidaq/control/access.hpp"
#include "minidaq/control/listmode_sink.hpp"
#include "minidaq/control/signing.hpp"
#include "minidaq/update/bundle.hpp"
#include "minidaq/update/slots.hpp"

namespace fs = std::filesystem;

namespace {

[[noreturn]] void fail() { std::abort(); }

void write(const fs::path& p, std::string_view text) {
  std::ofstream out{p, std::ios::binary | std::ios::trunc};
  out.write(text.data(), static_cast<std::streamsize>(text.size()));
  if (!out) {
    fail();
  }
}

struct PkeyFree {
  void operator()(EVP_PKEY* k) const { EVP_PKEY_free(k); }
};

// A directory of its own for this process, with a new Ed25519 key pair: run/ holds the record and
// its data file, keys/ the public key, store/ the update store.
struct Workspace {
  fs::path dir;
  std::unique_ptr<minidaq::signing::SigningKey> key;

  Workspace() {
    dir = fs::temp_directory_path() / ("minidaq-fuzz-documents-" + std::to_string(::getpid()));
    fs::remove_all(dir);
    fs::create_directories(dir / "run");
    fs::create_directories(dir / "keys");
    fs::create_directories(dir / "store");
    const std::unique_ptr<EVP_PKEY, PkeyFree> k{EVP_PKEY_Q_keygen(nullptr, nullptr, "ED25519")};
    if (!k) {
      fail();
    }
    std::FILE* f = std::fopen((dir / "site.key").c_str(), "wb");
    if (f == nullptr ||
        PEM_write_PrivateKey(f, k.get(), nullptr, nullptr, 0, nullptr, nullptr) != 1) {
      fail();
    }
    (void)std::fclose(f);
    f = std::fopen((dir / "keys" / "site.pem").c_str(), "wb");
    if (f == nullptr || PEM_write_PUBKEY(f, k.get()) != 1) {
      fail();
    }
    (void)std::fclose(f);
    auto loaded = minidaq::signing::SigningKey::load(dir / "site.key");
    if (!loaded) {
      fail();
    }
    key = std::make_unique<minidaq::signing::SigningKey>(*loaded);
    write(dir / "run" / "run-0000.mdql", "abc");
  }
  Workspace(const Workspace&) = delete;
  Workspace& operator=(const Workspace&) = delete;
  ~Workspace() {
    std::error_code ec;
    fs::remove_all(dir, ec);
  }
};

void signed_run(Workspace& w, std::string_view text) {
  const auto record = w.dir / "run" / "run.json";
  auto sig = w.key->sign(text);
  if (!sig) {
    fail();
  }
  write(record, text);
  write(record.string() + ".sig", *sig);
  const auto r = minidaq::control::verify_signed_run(record, w.dir / "keys");
  if (!r) {
    if (r.error().empty()) {
      fail();
    }
    return;
  }
  if (*r != "site.pem") {
    fail();
  }
  // Accepted: the record is an object whose files are run-0000.mdql only, three bytes each.
  const auto j = nlohmann::json::parse(text, nullptr, false);
  if (!j.is_object() || !j.contains("files") || !j["files"].is_array()) {
    fail();
  }
  for (const auto& f : j["files"]) {
    if (!f.is_string() || f.get<std::string>() != "run-0000.mdql") {
      fail();
    }
  }
}

void slot_state(Workspace& w, std::string_view text) {
  const auto store = w.dir / "store";
  write(store / "state.json", text);
  const auto s = minidaq::update::SlotStore::open(store);
  if (!s && s.error().empty()) {
    fail();
  }
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data, std::size_t size) {
  static Workspace w;
  if (size == 0) {
    return 0;
  }
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast): libFuzzer's bytes as text
  const std::string_view text{reinterpret_cast<const char*>(data + 1), size - 1};
  switch (data[0] % 5) {
    case 0: {
      const auto c = minidaq::config::parse_hardware_config(text);
      if (!c && c.error().empty()) {
        fail();
      }
      break;
    }
    case 1: {
      const auto m = minidaq::update::parse_manifest(text);
      if (!m && m.error().empty()) {
        fail();
      }
      break;
    }
    case 2: {
      const auto p = w.dir / "tokens.json";
      write(p, text);
      fs::permissions(p, fs::perms::owner_read | fs::perms::owner_write, fs::perm_options::replace);
      const auto t = minidaq::control::TokenStore::load(p);
      if (!t && t.error().empty()) {
        fail();
      }
      break;
    }
    case 3:
      signed_run(w, text);
      break;
    default:
      slot_state(w, text);
      break;
  }
  return 0;
}
