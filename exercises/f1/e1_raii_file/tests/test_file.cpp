#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>

#include <unistd.h>

#include "file.hpp"

using ex::File;

namespace {

// A scratch file name unique to this test case and process (ctest runs tests in parallel), removed
// when the guard goes out of scope.
struct ScratchPath {
  std::filesystem::path path;
  explicit ScratchPath(const std::string& name)
      : path{std::filesystem::temp_directory_path() /
             ("f1_e1_" + name + "_" + std::to_string(::getpid()))} {
    std::filesystem::remove(path);
  }
  ~ScratchPath() { std::filesystem::remove(path); }
  ScratchPath(const ScratchPath&) = delete;
  ScratchPath& operator=(const ScratchPath&) = delete;
};

std::string slurp(const std::filesystem::path& p) {
  std::ifstream in{p, std::ios::binary};
  return {std::istreambuf_iterator<char>{in}, std::istreambuf_iterator<char>{}};
}

}  // namespace

TEST(File, IsMoveOnly) {
  EXPECT_FALSE(std::is_copy_constructible_v<File>);
  EXPECT_FALSE(std::is_copy_assignable_v<File>);
  EXPECT_TRUE(std::is_nothrow_move_constructible_v<File>);
  EXPECT_TRUE(std::is_nothrow_move_assignable_v<File>);
}

TEST(File, OpenFailureIsReportedAndOpensNothing) {
  const int before = File::open_count();
  auto f = File::open("/nonexistent-directory/run-1.txt", "r");
  EXPECT_FALSE(f.has_value());
  EXPECT_EQ(File::open_count(), before);
}

TEST(File, DestructorClosesAndFlushes) {
  ScratchPath p{"dtor"};
  const int before = File::open_count();
  {
    auto f = File::open(p.path.string(), "w");
    ASSERT_TRUE(f.has_value());
    EXPECT_EQ(File::open_count(), before + 1);
    EXPECT_TRUE(f->write("run 1: 1200 singles\n"));
  }
  EXPECT_EQ(File::open_count(), before);
  EXPECT_EQ(slurp(p.path), "run 1: 1200 singles\n");
}

TEST(File, ClosesWhenAnExceptionLeavesTheScope) {
  ScratchPath p{"throw"};
  const int before = File::open_count();
  try {
    auto f = File::open(p.path.string(), "w");
    ASSERT_TRUE(f.has_value());
    f->write("partial\n");
    throw std::runtime_error{"decoder failed"};
  } catch (const std::runtime_error&) {
  }
  EXPECT_EQ(File::open_count(), before);
  EXPECT_EQ(slurp(p.path), "partial\n");
}

TEST(File, MoveTransfersOwnership) {
  ScratchPath p{"move"};
  const int before = File::open_count();
  {
    auto f = File::open(p.path.string(), "w");
    ASSERT_TRUE(f.has_value());
    File g = std::move(*f);
    EXPECT_FALSE(f->is_open());  // NOLINT(bugprone-use-after-move): a moved-from File is empty
    EXPECT_TRUE(g.is_open());
    EXPECT_TRUE(g.write("moved\n"));
    EXPECT_EQ(File::open_count(), before + 1);
  }
  EXPECT_EQ(File::open_count(), before);
  EXPECT_EQ(slurp(p.path), "moved\n");
}

TEST(File, MoveAssignmentClosesTheOldFile) {
  ScratchPath a{"assign_a"};
  ScratchPath b{"assign_b"};
  const int before = File::open_count();
  {
    auto fa = File::open(a.path.string(), "w");
    auto fb = File::open(b.path.string(), "w");
    ASSERT_TRUE(fa && fb);
    fa->write("a\n");
    fb->write("b\n");
    EXPECT_EQ(File::open_count(), before + 2);
    *fa = std::move(*fb);  // fa's file must be closed here, not leaked
    EXPECT_EQ(File::open_count(), before + 1);
    EXPECT_EQ(slurp(a.path), "a\n");
  }
  EXPECT_EQ(File::open_count(), before);
}

TEST(File, ExplicitCloseIsIdempotent) {
  ScratchPath p{"close"};
  const int before = File::open_count();
  auto f = File::open(p.path.string(), "w");
  ASSERT_TRUE(f.has_value());
  f->close();
  f->close();
  EXPECT_FALSE(f->is_open());
  EXPECT_FALSE(f->write("after close"));
  EXPECT_EQ(File::open_count(), before);
}

TEST(File, ReadsBackWhatWasWritten) {
  ScratchPath p{"read"};
  {
    auto w = File::open(p.path.string(), "w");
    ASSERT_TRUE(w.has_value());
    w->write("511 keV\n");
  }
  auto r = File::open(p.path.string(), "r");
  ASSERT_TRUE(r.has_value());
  EXPECT_EQ(r->read_all().value_or(""), "511 keV\n");
}
