// SPDX-License-Identifier: MIT
// Signed updates into two slots, with rollback (Chapter 25). The tests make their own signing
// keys, so no private key exists outside a test's temporary directory, and their own bundles
// with tar(1), as tools/make_update.py does on the release side.
#include <gtest/gtest.h>
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <unistd.h>

#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <functional>
#include <map>
#include <memory>
#include <nlohmann/json.hpp>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "minidaq/update/bundle.hpp"
#include "minidaq/update/slots.hpp"

using namespace minidaq::update;
namespace fs = std::filesystem;

namespace {

struct PkeyFree {
  void operator()(EVP_PKEY* k) const { EVP_PKEY_free(k); }
};
using Key = std::unique_ptr<EVP_PKEY, PkeyFree>;

// Only types whose generation takes no parameter (ED25519, ED448).
Key new_key(const char* type = "ED25519") { return Key{EVP_PKEY_Q_keygen(nullptr, nullptr, type)}; }

void write_public(const Key& key, const fs::path& file) {
  std::FILE* f = std::fopen(file.c_str(), "wb");
  ASSERT_NE(f, nullptr);
  ASSERT_EQ(PEM_write_PUBKEY(f, key.get()), 1);
  (void)std::fclose(f);
}

std::string sign(const Key& key, const std::string& message) {
  std::unique_ptr<EVP_MD_CTX, decltype(&EVP_MD_CTX_free)> ctx{EVP_MD_CTX_new(), EVP_MD_CTX_free};
  std::size_t len = 0;
  EXPECT_EQ(EVP_DigestSignInit(ctx.get(), nullptr, nullptr, nullptr, key.get()), 1);
  const auto* msg = reinterpret_cast<const unsigned char*>(
      message.data());  // NOLINT(cppcoreguidelines-pro-type-reinterpret-cast)
  EXPECT_EQ(EVP_DigestSign(ctx.get(), nullptr, &len, msg, message.size()), 1);
  std::string sig(len, '\0');
  EXPECT_EQ(EVP_DigestSign(ctx.get(), reinterpret_cast<unsigned char*>(sig.data()), &len, msg,
                           message.size()),
            1);  // NOLINT(cppcoreguidelines-pro-type-reinterpret-cast)
  return sig;
}

void write(const fs::path& p, const std::string& text) {
  fs::create_directories(p.parent_path());
  std::ofstream{p, std::ios::binary} << text;
}

std::string read(const fs::path& p) {
  std::ifstream in{p, std::ios::binary};
  std::ostringstream s;
  s << in.rdbuf();
  return s.str();
}

class Update : public ::testing::Test {
 protected:
  void SetUp() override {
    dir_ = fs::temp_directory_path() /
           ("minidaq-update-" + std::to_string(::getpid()) + "-" +
            ::testing::UnitTest::GetInstance()->current_test_info()->name());
    fs::remove_all(dir_);
    fs::create_directories(root());
    fs::create_directories(keys());
    write_public(key_, keys() / "release-2026.pem");
  }
  void TearDown() override { fs::remove_all(dir_); }

  [[nodiscard]] fs::path root() const { return dir_ / "opt"; }
  [[nodiscard]] fs::path keys() const { return dir_ / "keys"; }
  [[nodiscard]] InstallOptions options() const { return {keys(), "test-platform-1", false}; }

  // A bundle of `files` (path -> content) with its MANIFEST.sha256, signed with `key`.
  // `tamper` changes the stage after the manifest is written and before the archive.
  fs::path bundle(const std::string& version, std::map<std::string, std::string> files = {},
                  const std::function<void(const fs::path& stage)>& tamper = {},
                  const Key* key = nullptr, const std::string& platform = "test-platform-1") {
    if (files.empty()) {
      files = {{"bin/minidaq_server", "server " + version},
               {"share/minidaq/VERSION", version + "\n"}};
    }
    const fs::path out = dir_ / ("bundle-" + version + "-" + std::to_string(++count_));
    const fs::path stage = out / "stage";
    std::string manifest;
    for (const auto& [path, content] : files) {
      write(stage / path, content);
      manifest += digest_file(stage / path)->sha256 + "  " + path + "\n";
    }
    write(stage / "MANIFEST.sha256", manifest);
    if (tamper) {
      tamper(stage);
    }
    const std::string archive = "minidaq-" + version + ".tar.gz";
    const std::string cmd =
        "tar -czf '" + (out / archive).string() + "' -C '" + stage.string() + "' .";
    EXPECT_EQ(std::system(cmd.c_str()),
              0);  // NOLINT(cert-env33-c,concurrency-mt-unsafe): the test's own fixture
    const auto d = digest_file(out / archive);
    const nlohmann::json m{{"format", "minidaq-update 1"},
                           {"product", "minidaq"},
                           {"version", version},
                           {"commit", "abc1234"},
                           {"platform", platform},
                           {"archive", archive},
                           {"size", d->size},
                           {"sha256", d->sha256}};
    write(out / "update.json", m.dump(2));
    write(out / "update.json.sig", sign(key ? *key : key_, read(out / "update.json")));
    return out;
  }

  [[nodiscard]] std::string running() const {
    return read(root() / "current" / "bin" / "minidaq_server");
  }

  fs::path dir_;
  Key key_ = new_key();
  int count_ = 0;
};

TEST(UpdateVersion, OrdersReleasesAndTheirPreReleases) {
  // REQ: SRS-PLT-005
  const auto v = [](const char* s) { return *Version::parse(s); };
  EXPECT_LT(v("0.5.0"), v("0.5.1"));
  EXPECT_LT(v("0.5.9"), v("0.10.0")) << "numbers, not strings";
  EXPECT_LT(v("0.5.0-rc.1"), v("0.5.0")) << "a pre-release comes before its release";
  EXPECT_LT(v("0.5.0-rc.1"), v("0.5.0-rc.2"));
  EXPECT_EQ(v("1.2.3-dev").str(), "1.2.3-dev");
  for (const char* bad : {"", "1", "1.2", "1.2.3.4", "1.2.x", "1.2.3-", "-1.2.3", "v1.2.3"}) {
    EXPECT_FALSE(Version::parse(bad).has_value()) << bad;
  }
}

TEST(UpdateManifest, EveryFieldIsRequiredAndTheArchiveIsAPlainName) {
  // REQ: SRS-PLT-003
  nlohmann::json good{{"format", "minidaq-update 1"},
                      {"product", "minidaq"},
                      {"version", "0.5.0"},
                      {"commit", "abc"},
                      {"platform", "p"},
                      {"archive", "m.tar.gz"},
                      {"size", 10},
                      {"sha256", std::string(64, 'a')}};
  ASSERT_TRUE(parse_manifest(good.dump()).has_value());
  for (const char* key :
       {"format", "product", "version", "commit", "platform", "archive", "size", "sha256"}) {
    auto m = good;
    m.erase(key);
    EXPECT_FALSE(parse_manifest(m.dump()).has_value()) << key;
  }
  for (const char* archive :
       {"../m.tar.gz", "/tmp/m.tar.gz", "sub/m.tar.gz", ".m.tar.gz", "m.zip"}) {
    auto m = good;
    m["archive"] = archive;
    EXPECT_FALSE(parse_manifest(m.dump()).has_value()) << archive;
  }
  auto m = good;
  m["sha256"] = std::string(64, 'A');
  EXPECT_FALSE(parse_manifest(m.dump()).has_value()) << "uppercase digest";
  m = good;
  m["format"] = "minidaq-update 2";
  EXPECT_FALSE(parse_manifest(m.dump()).has_value());
}

TEST_F(Update, OnlyASignatureByATrustedEd25519KeyIsAccepted) {
  // REQ: SRS-PLT-003
  const std::string message = R"({"product": "minidaq"})";
  EXPECT_EQ(verify_signature(message, sign(key_, message), keys()).value_or(""),
            "release-2026.pem");

  std::string altered = message;
  altered[3] = 'P';
  EXPECT_FALSE(verify_signature(altered, sign(key_, message), keys()).has_value())
      << "a changed message";
  std::string sig = sign(key_, message);
  sig[10] = static_cast<char>(sig[10] ^ 1);
  EXPECT_FALSE(verify_signature(message, sig, keys()).has_value()) << "a changed signature";
  const Key stranger = new_key();
  EXPECT_FALSE(verify_signature(message, sign(stranger, message), keys()).has_value())
      << "an unknown key";

  // A second trusted key (the next one, before the old one is retired) verifies its own.
  write_public(stranger, keys() / "release-2027.pem");
  EXPECT_EQ(verify_signature(message, sign(stranger, message), keys()).value_or(""),
            "release-2027.pem");

  // A key of another type is never trusted, even with a valid signature of its own kind.
  const Key ed448 = new_key("ED448");
  write_public(ed448, keys() / "z-ed448.pem");
  EXPECT_FALSE(verify_signature(message, sign(ed448, message), keys()).has_value());
  EXPECT_FALSE(verify_signature(message, sign(key_, message), dir_ / "no-keys").has_value());
}

TEST_F(Update, InstallsATrialThatIsConfirmedOrRolledBack) {
  // REQ: SRS-PLT-004, SRS-PLT-006, SRS-PLT-010
  auto store = SlotStore::open(root());
  ASSERT_TRUE(store.has_value()) << store.error();
  auto r = store->install(bundle("0.5.0"), options());
  ASSERT_TRUE(r.has_value()) << r.error();
  EXPECT_EQ(running(), "server 0.5.0");
  EXPECT_EQ(store->current(), "a");
  EXPECT_FALSE(store->state()->trial.has_value()) << "the first installation is confirmed at once";

  r = store->install(bundle("0.5.1"), options());
  ASSERT_TRUE(r.has_value()) << r.error();
  EXPECT_EQ(running(), "server 0.5.1");
  EXPECT_EQ(store->current(), "b");
  EXPECT_EQ(store->state()->trial, "b");
  EXPECT_EQ(store->state()->good_version, "0.5.0");
  EXPECT_FALSE(store->install(bundle("0.5.2"), options()).has_value()) << "one trial at a time";

  EXPECT_EQ(store->rollback().value(), Outcome::done);
  EXPECT_EQ(running(), "server 0.5.0");
  EXPECT_EQ(store->current(), "a");
  EXPECT_EQ(store->rollback().value(), Outcome::nothing_to_do)
      << "a good version is never rolled back";

  ASSERT_TRUE(store->install(bundle("0.5.2"), options()).has_value());
  EXPECT_EQ(store->confirm().value(), Outcome::done);
  EXPECT_EQ(store->state()->good, "b");
  EXPECT_EQ(store->state()->good_version, "0.5.2");
  EXPECT_EQ(store->confirm().value(), Outcome::nothing_to_do);
  EXPECT_EQ(store->rollback().value(), Outcome::nothing_to_do);

  // The state outlives the process.
  store = SlotStore{std::move(*store)};
  const std::string history = read(root() / "history.jsonl");
  EXPECT_NE(history.find("\"rollback\""), std::string::npos);
  EXPECT_NE(history.find("\"confirm\""), std::string::npos);
}

TEST_F(Update, RefusesWhatTheSignatureDoesNotVouchFor) {
  // REQ: SRS-PLT-003, SRS-PLT-004, SRS-PLT-005
  auto store = SlotStore::open(root());
  ASSERT_TRUE(store.has_value());
  ASSERT_TRUE(store->install(bundle("0.5.0"), options()).has_value());
  const auto refused = [&](const fs::path& b, const std::string& why) {
    auto r = store->install(b, options());
    EXPECT_FALSE(r.has_value()) << why;
    if (!r) {
      EXPECT_NE(r.error().find(why), std::string::npos) << r.error();
    }
    EXPECT_EQ(running(), "server 0.5.0");
    EXPECT_FALSE(store->state()->trial.has_value());
  };

  const Key stranger = new_key();
  refused(bundle("0.6.0", {}, {}, &stranger), "does not verify");
  auto b = bundle("0.6.0");
  write(b / "update.json", read(b / "update.json") + " ");  // one byte more than was signed
  refused(b, "does not verify");
  b = bundle("0.6.0");
  std::ofstream{b / "minidaq-0.6.0.tar.gz", std::ios::app} << "x";
  refused(b, "not the archive the manifest describes");
  refused(bundle("0.6.0", {}, {}, nullptr, "other-platform"), "for the platform");
  refused(bundle("0.4.9"), "not newer");
  refused(bundle("0.5.0"), "not newer");
  refused(bundle("0.6.0", {}, [](const fs::path& s) { write(s / "bin/extra", "x"); }),
          "bin/extra is not in MANIFEST");
  refused(bundle("0.6.0", {}, [](const fs::path& s) { write(s / "bin/minidaq_server", "evil"); }),
          "does not match its digest");
  refused(bundle("0.6.0", {}, [](const fs::path& s) { fs::remove(s / "share/minidaq/VERSION"); }),
          "missing");
  refused(bundle("0.6.0", {},
                 [](const fs::path& s) { fs::create_symlink("/etc/passwd", s / "bin/link"); }),
          "not a regular file");

  auto older = options();
  older.allow_older = true;
  EXPECT_TRUE(store->install(bundle("0.4.9"), older).has_value())
      << "a downgrade that is asked for";
}

TEST_F(Update, RefusesAnArchiveThatWritesOutsideItsSlot) {
  // REQ: SRS-PLT-004
  auto store = SlotStore::open(root());
  ASSERT_TRUE(store.has_value());
  ASSERT_TRUE(store->install(bundle("0.5.0"), options()).has_value());
  // A signed manifest for an archive with a member "../escaped": the signature vouches only for
  // the archive's bytes, and a release tool can be wrong. (tar -P keeps the "../" that tar
  // would otherwise strip when it creates the archive.)
  const fs::path b = bundle("0.6.0");
  const fs::path stage = dir_ / "evil";
  write(stage / "inner" / "MANIFEST.sha256", "");
  write(stage / "escaped", "x");
  const std::string cmd = "tar -P -czf '" + (b / "minidaq-0.6.0.tar.gz").string() + "' -C '" +
                          (stage / "inner").string() + "' MANIFEST.sha256 ../escaped 2>/dev/null";
  ASSERT_EQ(std::system(cmd.c_str()),
            0);  // NOLINT(cert-env33-c,concurrency-mt-unsafe): the test's own fixture
  const auto d = digest_file(b / "minidaq-0.6.0.tar.gz");
  auto m = nlohmann::json::parse(read(b / "update.json"));
  m["size"] = d->size;
  m["sha256"] = d->sha256;
  write(b / "update.json", m.dump(2));
  write(b / "update.json.sig", sign(key_, read(b / "update.json")));
  auto r = store->install(b, options());
  ASSERT_FALSE(r.has_value());
  EXPECT_NE(r.error().find("outside its directory"), std::string::npos) << r.error();
  EXPECT_FALSE(fs::exists(root() / "slots" / "escaped"));
}

// [snippet:crash-test]
// A power cut after any step of any operation: the store opens again, `current` names a
// version whose files all verify, and that version is the good one or a trial on record.
TEST_F(Update, APowerCutAfterAnyStepLeavesAVersionThatRuns) {
  // REQ: SRS-PLT-007
  struct PowerCut : std::runtime_error {
    PowerCut() : std::runtime_error{"power cut"} {}
  };
  const std::vector<std::string> steps{"verified", "extracted", "checked", "recorded", "switched"};
  for (const std::string op : {"first install", "install", "confirm", "rollback"}) {
    for (const auto& at : steps) {
      fs::remove_all(root());
      fs::create_directories(root());
      if (op != "first install") {
        auto setup = SlotStore::open(root());
        ASSERT_TRUE(setup->install(bundle("1.0.0"), options()).has_value());
        if (op != "install") {
          ASSERT_TRUE(setup->install(bundle("1.1.0"), options()).has_value());
        }
      }
      const auto b = bundle(op == "install" ? "1.1.0" : "1.0.0");
      bool cut = false;
      {
        auto store = SlotStore::open(root(), [&](std::string_view step) {
          if (step == at) {
            cut = true;
            throw PowerCut{};
          }
        });
        ASSERT_TRUE(store.has_value());
        try {
          if (op == "first install" || op == "install") {
            (void)store->install(b, options());
          } else if (op == "confirm") {
            (void)store->confirm();
          } else {
            (void)store->rollback();
          }
        } catch (const PowerCut&) {
        }
      }
      SCOPED_TRACE(op + ", cut after " + at + (cut ? "" : " (no such step)"));
      auto after = SlotStore::open(root());
      ASSERT_TRUE(after.has_value()) << after.error();
      if (op == "first install" && !after->state()) {
        EXPECT_FALSE(fs::exists(root() / "current")) << "nothing installed, nothing runs";
        continue;
      }
      ASSERT_TRUE(after->state().has_value());
      const auto& st = *after->state();
      EXPECT_TRUE(after->current() == st.good || after->current() == st.trial.value_or("-"));
      EXPECT_TRUE(verify_tree(root() / "current").has_value()) << "the version that runs is whole";
      const std::string version = read(root() / "current" / "share/minidaq/VERSION");
      EXPECT_EQ(version, (after->current() == st.good ? st.good_version : st.trial_version) + "\n");
      // And the next operation works from here.
      EXPECT_TRUE(after->install(bundle("2.0.0"), options()).has_value() || st.trial.has_value());
    }
  }
}
// [/snippet:crash-test]

TEST_F(Update, OneProcessAtATime) {
  // REQ: SRS-PLT-011
  auto first = SlotStore::open(root());
  ASSERT_TRUE(first.has_value());
  auto second = SlotStore::open(root());
  ASSERT_FALSE(second.has_value());
  EXPECT_NE(second.error().find("another minidaq_update"), std::string::npos);
}

}  // namespace
