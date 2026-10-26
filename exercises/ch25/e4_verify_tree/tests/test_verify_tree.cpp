// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 25.4: an unpacked slot checked against its MANIFEST.sha256, with
// every way a tree can differ from what was signed.
#include <gtest/gtest.h>
#include <sys/stat.h>
#include <unistd.h>

#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

#include "verify_tree.hpp"

namespace fs = std::filesystem;
using Problems = std::vector<std::string>;

namespace {

constexpr const char* hello_sha256 =
    "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03";  // of "hello\n"

class Tree : public ::testing::Test {
 protected:
  void SetUp() override {
    std::string tmpl = (fs::temp_directory_path() / "ex25-4-XXXXXX").string();
    ASSERT_NE(::mkdtemp(tmpl.data()), nullptr);
    root = tmpl;
    file("bin/minidaq_server", "server\n");
    file("bin/minidaq_ctl", "ctl\n");
    file("share/minidaq/VERSION", "0.5.0\n");
    manifest = {line("bin/minidaq_ctl"), line("bin/minidaq_server"), line("share/minidaq/VERSION")};
    write_manifest();
  }
  void TearDown() override { fs::remove_all(root); }

  void file(const std::string& rel, const std::string& text) {
    fs::create_directories((root / rel).parent_path());
    std::ofstream{root / rel, std::ios::binary} << text;
  }
  std::string line(const std::string& rel) { return tree::sha256_of(root / rel) + "  " + rel; }
  void write_manifest() {
    std::ofstream out{root / "MANIFEST.sha256"};
    for (const auto& l : manifest) {
      out << l << '\n';
    }
  }

  fs::path root;
  std::vector<std::string> manifest;
};

}  // namespace

TEST_F(Tree, AnIntactTreeHasNoProblems) {
  EXPECT_EQ(tree::sha256_of(root / "missing"), "");
  file("hello", "hello\n");
  EXPECT_EQ(tree::sha256_of(root / "hello"), hello_sha256);
  manifest.push_back(line("hello"));
  write_manifest();
  EXPECT_EQ(tree::verify(root), Problems{});
}

TEST_F(Tree, FilesChangedMissingOrAdded) {
  file("bin/minidaq_server", "patched\n");
  fs::remove(root / "share/minidaq/VERSION");
  file("bin/helper", "x\n");
  file("etc/.hidden", "x\n");
  EXPECT_EQ(tree::verify(root),
            (Problems{"mismatch: bin/minidaq_server", "missing: share/minidaq/VERSION",
                      "unlisted: bin/helper", "unlisted: etc/.hidden"}));
}

TEST_F(Tree, LinksAndSpecialFilesAreNeverFollowed) {
  fs::remove(root / "bin/minidaq_ctl");
  fs::create_symlink("/bin/sh", root / "bin/minidaq_ctl");   // listed, and a link now
  fs::create_directory_symlink("/etc", root / "share/etc");  // a way out of the tree
  ASSERT_EQ(::mkfifo((root / "share/fifo").c_str(), 0600), 0);
  EXPECT_EQ(tree::verify(root),
            (Problems{"not a regular file: bin/minidaq_ctl", "not a regular file: share/etc",
                      "not a regular file: share/fifo"}));
}

TEST_F(Tree, ListedPathsMustStayInside) {
  manifest.push_back(std::string(64, 'a') + "  ../outside");
  manifest.push_back(std::string(64, 'a') + "  /etc/passwd");
  manifest.push_back(std::string(64, 'a') + "  bin/./minidaq_ctl");
  manifest.push_back(std::string(64, 'a') + "  bin//minidaq_ctl");
  manifest.push_back(line("bin/minidaq_ctl"));
  write_manifest();
  EXPECT_EQ(tree::verify(root),
            (Problems{"duplicate: bin/minidaq_ctl", "outside the tree: ../outside",
                      "outside the tree: /etc/passwd", "outside the tree: bin/./minidaq_ctl",
                      "outside the tree: bin//minidaq_ctl"}));
}

TEST_F(Tree, LinesThatAreNotDigestLines) {
  manifest.insert(manifest.begin(), "");
  manifest.push_back(std::string(64, 'A') + "  bin/x");  // uppercase
  manifest.push_back(std::string(63, 'a') + "  bin/x");  // too short
  manifest.push_back(std::string(64, 'a') + " *bin/x");  // binary-mode marker
  manifest.push_back(std::string(64, 'a') + "  ");       // no path
  write_manifest();
  EXPECT_EQ(tree::verify(root),
            (Problems{"bad line: 1", "bad line: 5", "bad line: 6", "bad line: 7", "bad line: 8"}));
}

TEST_F(Tree, NoManifestNothingToTrust) {
  fs::remove(root / "MANIFEST.sha256");
  EXPECT_EQ(tree::verify(root), Problems{"missing: MANIFEST.sha256"});
}
