// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <unistd.h>

#include <cerrno>
#include <fstream>
#include <string>

#include "legacy_tool.hpp"

using namespace ex71;

TEST(Options, HappyPath) {
  Options o;
  ASSERT_TRUE(parse_options({"--port", "7701", "--rate", "2.5e6", "--repeat", "3"}, o));
  EXPECT_EQ(o.port, 7701);
  EXPECT_EQ(o.rate_hz, 2.5e6);
  EXPECT_EQ(o.repeat, 3);
}

TEST(Options, RejectsWhatAtoiAccepts) {
  Options o;
  EXPECT_FALSE(parse_options({"--port", "7OO"}, o)) << "atoi reads 7";
  EXPECT_FALSE(parse_options({"--port", "65536"}, o)) << "wraps to 0: any free port";
  EXPECT_FALSE(parse_options({"--port", "0"}, o)) << "a client needs a real port";
  EXPECT_FALSE(parse_options({"--rate", "fast"}, o)) << "atof reads 0";
  EXPECT_FALSE(parse_options({"--rate", "inf"}, o));
  EXPECT_FALSE(parse_options({"--rate", "-1"}, o)) << "a rate is positive";
  EXPECT_FALSE(parse_options({"--repeat", "-5"}, o)) << "at least once";
  EXPECT_FALSE(parse_options({"--repeat"}, o)) << "an option without its value";
  EXPECT_FALSE(parse_options({"--colour", "red"}, o));
}

TEST(Options, AFailedParseLeavesTheOptionsUnchanged) {
  Options o;
  EXPECT_FALSE(parse_options({"--port", "7701", "--rate", "x"}, o));
  EXPECT_EQ(o.port, 7700) << "all or nothing: do not half-apply a command line";
}

TEST(RecordFile, WritesLines) {
  const std::string path = ::testing::TempDir() + "ex71-" + std::to_string(::getpid()) + ".txt";
  {
    RecordFile f{path};
    ASSERT_TRUE(f.is_open());
    EXPECT_TRUE(f.write("one"));
    EXPECT_TRUE(f.write("two"));
    EXPECT_TRUE(f.close());
    EXPECT_FALSE(f.is_open());
    EXPECT_FALSE(f.close()) << "closing twice is an error, not a crash";
  }
  std::ifstream in{path};
  std::string a;
  std::string b;
  std::getline(in, a);
  std::getline(in, b);
  EXPECT_EQ(a + "," + b, "one,two");
  ::unlink(path.c_str());
}

TEST(RecordFile, AFullDiskIsReported) {
  RecordFile f{"/dev/full"};  // every write fails with ENOSPC, at the latest when flushed
  ASSERT_TRUE(f.is_open());
  (void)f.write("lost");     // buffered: may still report success
  EXPECT_FALSE(f.close()) << "the record was lost; close() must say so";
}

TEST(RecordFile, WritingToAFileThatDidNotOpenFails) {
  RecordFile f{"/nonexistent-dir/x.txt"};
  EXPECT_FALSE(f.is_open());
  EXPECT_FALSE(f.write("x")) << "not a null-pointer dereference";
}

TEST(LastError, NamesTheError) {
  errno = ENOENT;
  EXPECT_NE(last_error().find("No such file"), std::string::npos);
}
