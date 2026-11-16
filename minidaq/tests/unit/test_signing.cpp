// SPDX-License-Identifier: MIT
// Signed run records and calibration tables (release 1.3.0, CR-0027, ADR 0034; threats T-27 and
// T-54). Every key is made by the test in its own temporary directory: no private key exists in
// the repository.
#include <gtest/gtest.h>
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <unistd.h>

#include <cstdio>
#include <filesystem>
#include <fstream>
#include <memory>
#include <optional>
#include <sstream>
#include <string>

#include <nlohmann/json.hpp>

#include "calibration_fixture.hpp"
#include "eventually.hpp"
#include "minidaq/control/acquisition_service.hpp"
#include "minidaq/control/adapters.hpp"
#include "minidaq/control/listmode_sink.hpp"
#include "minidaq/control/signing.hpp"

using namespace minidaq;
using namespace minidaq::control;
namespace fs = std::filesystem;

namespace {

struct PkeyFree {
  void operator()(EVP_PKEY* k) const { EVP_PKEY_free(k); }
};

// A new Ed25519 key pair: the private key in `private_pem`, the public key in `public_pem`.
void make_key(const fs::path& private_pem, const fs::path& public_pem) {
  const std::unique_ptr<EVP_PKEY, PkeyFree> key{EVP_PKEY_Q_keygen(nullptr, nullptr, "ED25519")};
  ASSERT_NE(key, nullptr);
  std::FILE* f = std::fopen(private_pem.c_str(), "wb");
  ASSERT_NE(f, nullptr);
  ASSERT_EQ(PEM_write_PrivateKey(f, key.get(), nullptr, nullptr, 0, nullptr, nullptr), 1);
  (void)std::fclose(f);
  f = std::fopen(public_pem.c_str(), "wb");
  ASSERT_NE(f, nullptr);
  ASSERT_EQ(PEM_write_PUBKEY(f, key.get()), 1);
  (void)std::fclose(f);
}

std::string read(const fs::path& p) {
  std::ifstream in{p, std::ios::binary};
  std::ostringstream s;
  s << in.rdbuf();
  return s.str();
}

void write(const fs::path& p, const std::string& text) {
  std::ofstream{p, std::ios::binary} << text;
}

class Signing : public ::testing::Test {
 protected:
  void SetUp() override {
    dir_ = fs::temp_directory_path() /
           ("minidaq-sign-" + std::to_string(::getpid()) + "-" +
            ::testing::UnitTest::GetInstance()->current_test_info()->name());
    fs::remove_all(dir_);
    fs::create_directories(dir_ / "keys");
    fs::create_directories(dir_ / "other");
    fs::create_directories(dir_ / "data");
    make_key(dir_ / "site.key", dir_ / "keys" / "site.pem");
    make_key(dir_ / "other.key", dir_ / "other" / "other.pem");
  }
  void TearDown() override { fs::remove_all(dir_); }

  [[nodiscard]] std::shared_ptr<const signing::SigningKey> key(
      const char* name = "site.key") const {
    auto k = signing::SigningKey::load(dir_ / name);
    EXPECT_TRUE(k) << k.error();
    return std::make_shared<const signing::SigningKey>(std::move(*k));
  }

  // Runs a short acquisition into data/ with the list-mode sink and returns the run record's path.
  [[nodiscard]] fs::path run(const std::shared_ptr<const signing::SigningKey>& k) const {
    AcquisitionService svc{with_default_adapters({}, k)};
    config::AcquisitionConfig c;
    c.source.rate_hz = 2e6;
    c.source.stop_after_s = 0.05;
    c.output.type = "listmode";
    c.output.directory = (dir_ / "data").string();
    c.output.max_file_mib = 1;
    EXPECT_TRUE(svc.configure(c, "test").ok);
    EXPECT_TRUE(svc.start("test").ok);
    EXPECT_TRUE(svc.wait_for(AcqState::configured, test_support::patience)) << svc.status().dump();
    for (const auto& e : fs::directory_iterator{dir_ / "data"}) {
      if (e.path().string().ends_with(".run.json")) {
        return e.path();
      }
    }
    ADD_FAILURE() << "no run record";
    return {};
  }

  fs::path dir_;
};

TEST_F(Signing, SignsAndVerifiesWithTheKeysOfADirectory) {
  // REQ: SRS-PLT-003
  const auto k = key();
  const auto sig = k->sign("the message");
  ASSERT_TRUE(sig) << sig.error();
  EXPECT_EQ(sig->size(), 64U);
  const auto who = signing::verify("the message", *sig, dir_ / "keys");
  ASSERT_TRUE(who) << who.error();
  EXPECT_EQ(*who, "site.pem");
  EXPECT_FALSE(signing::verify("the messagE", *sig, dir_ / "keys")) << "a changed message";
  EXPECT_FALSE(signing::verify("the message", *sig, dir_ / "other")) << "a key nobody installed";
  EXPECT_FALSE(signing::verify("the message", "", dir_ / "keys")) << "no signature";
  EXPECT_FALSE(signing::verify("the message", *sig, dir_ / "none")) << "no trust store";
  EXPECT_EQ(k->key_id().size(), 64U);
  EXPECT_EQ(k->key_id(), key()->key_id()) << "the same key has the same id";
  EXPECT_NE(k->key_id(), key("other.key")->key_id());
  EXPECT_FALSE(signing::SigningKey::load(dir_ / "keys" / "site.pem")) << "a public key cannot sign";
  EXPECT_FALSE(signing::SigningKey::load(dir_ / "missing.key"));

  signing::Sha256 h;
  h.update(std::as_bytes(std::span{std::string_view{"abc"}}));
  EXPECT_EQ(h.hex_digest(),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");  // FIPS 180-2
}

TEST_F(Signing, ASignedRunVerifiesUntilAFileOrItsRecordChanges) {
  // REQ: SRS-OUT-013
  // REQ: SRS-OUT-014
  const auto k = key();
  const fs::path record = run(k);
  ASSERT_FALSE(record.empty());
  const auto j = nlohmann::json::parse(read(record));
  ASSERT_GE(j["files"].size(), 1U);
  ASSERT_EQ(j["file_digests"].size(), j["files"].size());
  EXPECT_EQ(j["signature"]["algorithm"], "Ed25519");
  EXPECT_EQ(j["signature"]["key_id"], k->key_id());
  const fs::path first = record.parent_path() / j["files"][0].get<std::string>();
  EXPECT_EQ(j["file_digests"][0]["bytes"].get<std::uint64_t>(), fs::file_size(first));

  const auto ok = verify_signed_run(record, dir_ / "keys");
  ASSERT_TRUE(ok) << ok.error();
  EXPECT_EQ(*ok, "site.pem");
  EXPECT_FALSE(verify_signed_run(record, dir_ / "other")) << "a key the site did not install";

  // A byte of a data file changed, with a valid MDQ-L1 CRC or not: the digest differs.
  const std::string data = read(first);
  std::string changed = data;
  changed[changed.size() / 2] = static_cast<char>(changed[changed.size() / 2] ^ 1);
  write(first, changed);
  const auto tampered = verify_signed_run(record, dir_ / "keys");
  ASSERT_FALSE(tampered);
  EXPECT_NE(tampered.error().find("SHA-256"), std::string::npos) << tampered.error();
  write(first, data);
  ASSERT_TRUE(verify_signed_run(record, dir_ / "keys"));

  // The record changed, for example a counter that would make the run look complete.
  const std::string text = read(record);
  write(record, text + " ");
  EXPECT_FALSE(verify_signed_run(record, dir_ / "keys")) << "a changed record";
  write(record, text);

  // A file removed, and the signature removed.
  fs::rename(first, first.string() + ".away");
  EXPECT_FALSE(verify_signed_run(record, dir_ / "keys")) << "a missing file";
  fs::rename(first.string() + ".away", first);
  fs::remove(record.string() + ".sig");
  const auto unsigned_run = verify_signed_run(record, dir_ / "keys");
  ASSERT_FALSE(unsigned_run);
  EXPECT_NE(unsigned_run.error().find("signature"), std::string::npos) << unsigned_run.error();
}

TEST_F(Signing, ASignedRecordThatDoesNotListItsFilesProperlyIsRefused) {
  // REQ: SRS-OUT-014
  // A trusted key can sign a record that is malformed: the check refuses it instead of
  // believing it. Each record below is signed again, so that only the content is wrong.
  const auto k = key();
  const fs::path record = run(k);
  ASSERT_FALSE(record.empty());
  const auto good = nlohmann::json::parse(read(record));
  const auto refused = [&](const nlohmann::json& j, const char* what) {
    const std::string text = j.dump();
    write(record, text);
    write(record.string() + ".sig", *k->sign(text));
    const auto r = verify_signed_run(record, dir_ / "keys");
    EXPECT_FALSE(r) << what;
    return r ? std::string{} : r.error();
  };
  auto j = good;
  j.erase("file_digests");
  EXPECT_NE(refused(j, "no digests").find("do not match"), std::string::npos);
  j = good;
  j["file_digests"].push_back(good["file_digests"][0]);
  EXPECT_NE(refused(j, "one digest too many").find("do not match"), std::string::npos);
  j = good;
  j["file_digests"][0]["file"] = "other.lm";
  EXPECT_NE(refused(j, "a digest of another file").find("has no digest"), std::string::npos);
  j = good;
  j["files"][0] = 7;
  EXPECT_NE(refused(j, "a file that is not a name").find("has no digest"), std::string::npos);
  j = good;
  j["files"][0] = "../" + good["files"][0].get<std::string>();
  j["file_digests"][0]["file"] = j["files"][0];
  EXPECT_NE(refused(j, "a path out of the run's directory").find("not a path"), std::string::npos);
  j = good;
  j["file_digests"][0]["bytes"] = good["file_digests"][0]["bytes"].get<std::uint64_t>() + 1;
  EXPECT_NE(refused(j, "a wrong size").find("size or SHA-256"), std::string::npos);
  j = good;
  j["files"][0] = "missing.lm";
  j["file_digests"][0]["file"] = "missing.lm";
  EXPECT_NE(refused(j, "a file that is not there").find("cannot read"), std::string::npos);
  // MDQ-PR-071: a field of the wrong type is a refusal, not an exception.
  const auto with_digest = [&](const char* field, const nlohmann::json& value) {
    auto m = good;
    m["file_digests"][0][field] = value;
    return m;
  };
  EXPECT_NE(refused(with_digest("sha256", 7), "a SHA-256 that is a number").find("no SHA-256"),
            std::string::npos);
  EXPECT_NE(refused(with_digest("bytes", "12"), "a size that is a string").find("no size"),
            std::string::npos);
  EXPECT_NE(refused(with_digest("bytes", -1), "a negative size").find("no size"),
            std::string::npos);
  j = good;
  j["file_digests"][0].erase("sha256");
  EXPECT_NE(refused(j, "no SHA-256").find("no SHA-256"), std::string::npos);
  EXPECT_NE(
      refused(with_digest("file", 7), "a digest whose file is a number").find("has no digest"),
      std::string::npos);
  j = good;
  j["file_digests"][0] = "run-0000.mdql";
  EXPECT_NE(refused(j, "a digest that is not an object").find("has no digest"), std::string::npos);
  j = good;
  j["file_digests"][0].erase("file");
  EXPECT_NE(refused(j, "a digest without its file").find("has no digest"), std::string::npos);
  j = good;
  j["file_digests"][0].erase("bytes");
  EXPECT_NE(refused(j, "no size").find("no size"), std::string::npos);
  for (const char* name : {"", ".", ".."}) {
    j = good;
    j["files"][0] = name;
    j["file_digests"][0]["file"] = name;
    EXPECT_NE(refused(j, name).find("not a path"), std::string::npos) << '"' << name << '"';
  }
  fs::create_directory(record.parent_path() / "sub");
  j = good;
  j["files"][0] = "sub";
  j["file_digests"][0]["file"] = "sub";
  j["file_digests"][0]["bytes"] = 0;
  j["file_digests"][0]["sha256"] = signing::Sha256{}.hex_digest();  // of no bytes
  EXPECT_NE(refused(j, "a directory").find("cannot read"), std::string::npos);
  write(record, "not json");
  write(record.string() + ".sig", *k->sign("not json"));
  EXPECT_FALSE(verify_signed_run(record, dir_ / "keys")) << "a signed text that is not JSON";
  EXPECT_FALSE(verify_signed_run(dir_ / "data" / "none.run.json", dir_ / "keys")) << "no record";
}

TEST_F(Signing, AnEncryptedKeyIsRefusedWithoutAskingForAPassphrase) {
  // REQ: SRS-OUT-013
  // MDQ-PR-073: OpenSSL's default answer to an encrypted key is a passphrase prompt on the
  // terminal, where a server started by systemd waits for nobody. The key is refused instead.
  const std::unique_ptr<EVP_PKEY, PkeyFree> key{EVP_PKEY_Q_keygen(nullptr, nullptr, "ED25519")};
  ASSERT_NE(key, nullptr);
  const fs::path pem = dir_ / "encrypted.pem";
  std::FILE* f = std::fopen(pem.c_str(), "wb");
  ASSERT_NE(f, nullptr);
  std::string pass = "a passphrase";
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast): OpenSSL takes bytes
  ASSERT_EQ(PEM_write_PrivateKey(f, key.get(), EVP_aes_256_cbc(),
                                 reinterpret_cast<unsigned char*>(pass.data()),
                                 static_cast<int>(pass.size()), nullptr, nullptr),
            1);
  (void)std::fclose(f);
  const auto loaded = signing::SigningKey::load(pem);
  ASSERT_FALSE(loaded);
  EXPECT_NE(loaded.error().find("is encrypted"), std::string::npos) << loaded.error();
  EXPECT_NE(loaded.error().find("openssl pkey"), std::string::npos)
      << "says how to store it unencrypted";
}

TEST_F(Signing, WithoutAKeyTheRunRecordIsAsBefore) {
  // REQ: SRS-OUT-013
  const fs::path record = run(nullptr);
  ASSERT_FALSE(record.empty());
  const auto j = nlohmann::json::parse(read(record));
  EXPECT_FALSE(j.contains("file_digests"));
  EXPECT_FALSE(j.contains("signature"));
  EXPECT_FALSE(fs::exists(record.string() + ".sig"));
  EXPECT_FALSE(verify_signed_run(record, dir_ / "keys"))
      << "an unsigned run does not pass for a signed one";
}

TEST_F(Signing, ACalibrationTableIsUsedOnlyWithASignatureATrustedKeyVerifies) {
  // REQ: SRS-CAL-008
  const fs::path table = dir_ / "table.json";
  const std::string text = calibration_fixture::good_table().dump();
  write(table, text);
  ServiceOptions o = with_default_adapters();
  const fs::path keys = dir_ / "keys";
  o.calibration_verifier = [keys](std::string_view t,
                                  std::string_view s) -> std::optional<std::string> {
    auto who = signing::verify(t, s, keys);
    return who ? std::nullopt : std::optional<std::string>{who.error()};
  };
  config::AcquisitionConfig c;
  c.calibration.file = table.string();
  c.calibration.scanner_serial = "MDQ-REF-0001";

  AcquisitionService svc{o};
  auto r = svc.configure(c, "test");
  EXPECT_FALSE(r.ok) << "no signature";
  EXPECT_NE(r.message.find("signature"), std::string::npos) << r.message;

  write(table.string() + ".sig", *key("other.key")->sign(text));
  EXPECT_FALSE(svc.configure(c, "test").ok) << "signed with a key the server does not trust";

  write(table.string() + ".sig", *key()->sign(text));
  r = svc.configure(c, "test");
  EXPECT_TRUE(r.ok) << r.message;

  // A coefficient changed within the limits: the signature is checked before the table is
  // parsed, so the refusal names the signature, whether or not the CRC was recomputed (T-54).
  auto j = calibration_fixture::good_table();
  j["time"]["offset_ps"][0] = 250;
  write(table, j.dump());
  r = svc.configure(c, "test");
  EXPECT_FALSE(r.ok) << "a changed table";
  EXPECT_NE(r.message.find("signature"), std::string::npos) << r.message;

  // Without a verifier, the table is checked as before and needs no signature.
  fs::remove(table.string() + ".sig");
  write(table, text);
  AcquisitionService plain{with_default_adapters()};
  EXPECT_TRUE(plain.configure(c, "test").ok);
}

}  // namespace
