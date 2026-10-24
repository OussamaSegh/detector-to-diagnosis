// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <fcntl.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <unistd.h>

#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <future>
#include <string>
#include <thread>

#include "untrusted_file.hpp"

using ex74::read_untrusted_file;
namespace fs = std::filesystem;

namespace {
// Runs in the death-test child: exit status 0 if /dev/zero was rejected.
[[noreturn]] void read_dev_zero_with_limits() {
#if !defined(__SANITIZE_ADDRESS__) && !defined(__SANITIZE_THREAD__)
  const rlimit limit{std::size_t{512} << 20, std::size_t{512} << 20};
  ::setrlimit(RLIMIT_AS, &limit);
#endif
  ::alarm(5);
  std::_Exit(read_untrusted_file("/dev/zero", 64) ? 1 : 0);
}

class UntrustedFile : public ::testing::Test {
 protected:
  void SetUp() override {
    dir_ = fs::path{::testing::TempDir()} / ("ex74-" + std::to_string(::getpid()));
    fs::create_directories(dir_);
  }
  void TearDown() override { fs::remove_all(dir_); }
  fs::path write(const std::string& name, const std::string& text) {
    const auto p = dir_ / name;
    std::ofstream{p} << text;
    fs::permissions(p, fs::perms::owner_read | fs::perms::owner_write | fs::perms::group_read);
    return p;
  }
  fs::path dir_;
};
}  // namespace

TEST_F(UntrustedFile, ReadsASmallRegularFile) {
  const auto r = read_untrusted_file(write("a.conf", "source.cpu = 1\n"), 64);
  ASSERT_TRUE(r) << r.error();
  EXPECT_EQ(*r, "source.cpu = 1\n");
  EXPECT_TRUE(read_untrusted_file(write("exact", std::string(64, 'x')), 64)) << "the limit itself is allowed";
  EXPECT_TRUE(read_untrusted_file(write("empty", ""), 64));
}

TEST_F(UntrustedFile, RejectsLargeFiles) {
  const auto r = read_untrusted_file(write("big", std::string(65, 'x')), 64);
  ASSERT_FALSE(r);
  EXPECT_NE(r.error().find("larger"), std::string::npos) << r.error();
}

TEST_F(UntrustedFile, RejectsDevicesAndDirectories) {
  EXPECT_FALSE(read_untrusted_file(dir_.string(), 64));
  // /dev/zero never ends: a reader without a size check reads until memory
  // runs out. Run it in a child process with a memory limit and a deadline,
  // so that a wrong solution fails this test instead of the machine.
  EXPECT_EXIT(read_dev_zero_with_limits(), ::testing::ExitedWithCode(0), "");
}

TEST_F(UntrustedFile, RejectsASymbolicLink) {
  // The classic attack: a link from a name you are allowed to give to a file you
  // should not be able to read through this program.
  const auto target = write("target", "secret");
  fs::create_symlink(target, dir_ / "link");
  const auto r = read_untrusted_file((dir_ / "link").string(), 64);
  ASSERT_FALSE(r);
  EXPECT_NE(r.error().find("symbolic link"), std::string::npos) << r.error();
}

TEST_F(UntrustedFile, RejectsAWorldWritableFile) {
  const auto p = write("open-to-all", "x");
  fs::permissions(p, fs::perms::others_write, fs::perm_options::add);
  EXPECT_FALSE(read_untrusted_file(p.string(), 64));
}

TEST_F(UntrustedFile, DoesNotBlockOnAFifo) {
  const auto fifo = dir_ / "fifo";
  ASSERT_EQ(::mkfifo(fifo.c_str(), 0600), 0);
  std::promise<bool> done;
  auto result = done.get_future();
  std::thread{[&done, path = fifo.string()] { done.set_value(static_cast<bool>(read_untrusted_file(path, 64))); }}
      .detach();
  const bool returned = result.wait_for(std::chrono::seconds{2}) == std::future_status::ready;
  if (!returned) {
    // Release the blocked reader: a writer that opens and closes gives it end of file.
    const int w = ::open(fifo.c_str(), O_WRONLY | O_NONBLOCK);
    if (w >= 0) {
      ::close(w);
    }
    result.wait();
  }
  EXPECT_TRUE(returned) << "opening a FIFO without a writer blocked the caller";
  EXPECT_FALSE(result.get()) << "a FIFO is not a regular file";
}

TEST_F(UntrustedFile, ErrorsNameThePath) {
  const auto r = read_untrusted_file((dir_ / "missing").string(), 64);
  ASSERT_FALSE(r);
  EXPECT_NE(r.error().find("missing"), std::string::npos);
}
