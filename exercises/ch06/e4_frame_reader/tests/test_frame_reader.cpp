// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 6.4.
#include <gtest/gtest.h>

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <future>
#include <memory>
#include <random>
#include <string>
#include <thread>
#include <vector>

#include "frame_reader.hpp"

using namespace std::chrono_literals;

namespace {

std::vector<std::byte> bytes(const std::string& s) {
  std::vector<std::byte> out;
  for (char c : s) {
    out.push_back(static_cast<std::byte>(c));
  }
  return out;
}

template <typename F>
void within(std::chrono::milliseconds limit, F f, const char* what) {
  auto done = std::make_shared<std::promise<void>>();
  auto fut = done->get_future();
  std::thread([done, f]() mutable {
    f();
    done->set_value();
  }).detach();
  if (fut.wait_for(limit) != std::future_status::ready) {
    std::fprintf(stderr, "watchdog: %s did not finish within %lld ms\n", what, static_cast<long long>(limit.count()));
    std::_Exit(1);
  }
}

}  // namespace

TEST(FrameReader, EncodesTheLengthBigEndian) {
  const auto f = ex::encode_frame(bytes("abc"));
  ASSERT_EQ(f.size(), 7U);
  EXPECT_EQ(f[0], std::byte{0});
  EXPECT_EQ(f[3], std::byte{3});
  EXPECT_EQ(f[4], std::byte{'a'});
  const std::vector<std::byte> big(0x0304);
  const auto g = ex::encode_frame(big);
  EXPECT_EQ(g[2], std::byte{0x03});
  EXPECT_EQ(g[3], std::byte{0x04});
}

TEST(FrameReader, OneFrameInOnePiece) {
  ex::FrameReader r{1024};
  r.feed(ex::encode_frame(bytes("hello")));
  const auto f = r.next();
  ASSERT_TRUE(f.has_value());
  EXPECT_EQ(*f, bytes("hello"));
  EXPECT_FALSE(r.next().has_value());
  EXPECT_EQ(r.buffered(), 0U);
}

TEST(FrameReader, OneByteAtATime) {
  ex::FrameReader r{1024};
  const auto wire = ex::encode_frame(bytes("split everywhere"));
  for (std::size_t i = 0; i + 1 < wire.size(); ++i) {
    r.feed(std::span{wire}.subspan(i, 1));
    ASSERT_FALSE(r.next().has_value()) << "complete after only " << i + 1 << " bytes";
  }
  r.feed(std::span{wire}.last(1));
  EXPECT_EQ(r.next(), bytes("split everywhere"));
}

TEST(FrameReader, ManyFramesInOneReadAndEmptyFrames) {
  ex::FrameReader r{1024};
  std::vector<std::byte> wire;
  for (const char* s : {"a", "", "bc", ""}) {
    const auto f = ex::encode_frame(bytes(s));
    wire.insert(wire.end(), f.begin(), f.end());
  }
  r.feed(wire);
  EXPECT_EQ(r.next(), bytes("a"));
  EXPECT_EQ(r.next(), bytes(""));
  EXPECT_EQ(r.next(), bytes("bc"));
  EXPECT_EQ(r.next(), bytes(""));
  EXPECT_FALSE(r.next().has_value());
}

TEST(FrameReader, RandomChunkingGivesTheSameFrames) {
  std::mt19937 rng(42);
  std::vector<std::vector<std::byte>> sent;
  std::vector<std::byte> wire;
  for (int i = 0; i < 2000; ++i) {
    std::vector<std::byte> p(rng() % 300);
    for (auto& b : p) {
      b = static_cast<std::byte>(rng());
    }
    const auto f = ex::encode_frame(p);
    wire.insert(wire.end(), f.begin(), f.end());
    sent.push_back(std::move(p));
  }
  ex::FrameReader r{300};
  std::vector<std::vector<std::byte>> got;
  for (std::size_t pos = 0; pos < wire.size();) {
    const std::size_t n = std::min<std::size_t>(1 + rng() % 700, wire.size() - pos);
    r.feed(std::span{wire}.subspan(pos, n));
    pos += n;
    while (auto f = r.next()) {
      got.push_back(std::move(*f));
    }
  }
  EXPECT_EQ(got.size(), sent.size());
  EXPECT_TRUE(got == sent);
  EXPECT_EQ(r.buffered(), 0U);
  EXPECT_FALSE(r.failed());
}

TEST(FrameReader, TooLargeIsDetectedFromTheHeaderAndIsPermanent) {
  ex::FrameReader r{100};
  std::vector<std::byte> ok(100);
  r.feed(ex::encode_frame(ok));
  ASSERT_TRUE(r.next().has_value()) << "exactly the maximum is allowed";
  const std::vector<std::byte> header{std::byte{0}, std::byte{0}, std::byte{0}, std::byte{101}};
  r.feed(header);  // no payload yet: must fail now, not after buffering 101 bytes
  EXPECT_FALSE(r.next().has_value());
  EXPECT_TRUE(r.failed());
  r.feed(ex::encode_frame(bytes("x")));
  EXPECT_FALSE(r.next().has_value()) << "no resynchronization after a bad length";
  EXPECT_TRUE(r.failed());
}

TEST(FrameReader, HugeLengthDoesNotAllocate) {
  ex::FrameReader r{1 << 20};
  const std::vector<std::byte> header{std::byte{0xFF}, std::byte{0xFF}, std::byte{0xFF}, std::byte{0xFF}};
  r.feed(header);
  EXPECT_FALSE(r.next().has_value());
  EXPECT_TRUE(r.failed());
}

TEST(FrameReader, CostIsLinearInTheBytesReceived) {
  // Many tiny frames in one read. Erasing each consumed frame from the front
  // of the buffer moves the rest every time, so 4x the frames cost 16x the
  // time. Comparing two sizes keeps the test meaningful under sanitizers.
  within(
      30'000ms,
      [] {
        const auto time_for = [](int frames) {
          std::vector<std::byte> wire;
          for (int i = 0; i < frames; ++i) {
            const auto f = ex::encode_frame(bytes("xy"));
            wire.insert(wire.end(), f.begin(), f.end());
          }
          ex::FrameReader r{16};
          const auto t0 = std::chrono::steady_clock::now();
          r.feed(wire);
          int n = 0;
          while (r.next()) {
            ++n;
          }
          EXPECT_EQ(n, frames);
          return std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
        };
        const double small = time_for(250'000);
        const double large = time_for(1'000'000);
        EXPECT_LT(large, 8.0 * small + 50.0) << "4x the frames took " << large / small << "x the time: quadratic?";
      },
      "250,000 and 1,000,000 frames");
}
