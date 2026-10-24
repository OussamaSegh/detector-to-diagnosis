// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <unistd.h>

#include <fstream>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

#include "minidaq/control/audit_log.hpp"

using namespace minidaq::control;

namespace {
AuditRecord record(std::string detail) { return {"2026-10-24T12:00:00.000Z", "test", "configure", std::move(detail), true}; }
}  // namespace

TEST(AuditLog, AppendsOneJsonObjectPerLine) {
  const std::string path = ::testing::TempDir() + "audit-" + std::to_string(::getpid()) + ".jsonl";
  {
    JsonLinesAuditLog log{path};
    ASSERT_TRUE(log.is_open());
    log.append(record("first"));
    log.sink()(record("second \xff"));  // invalid UTF-8 from a client is replaced, not thrown
    EXPECT_EQ(log.failed_writes(), 0U);
  }
  std::ifstream in{path};
  std::string line;
  std::vector<nlohmann::json> lines;
  while (std::getline(in, line)) {
    lines.push_back(nlohmann::json::parse(line));
  }
  ASSERT_EQ(lines.size(), 2U);
  EXPECT_EQ(lines[0]["detail"], "first");
  EXPECT_EQ(lines[1]["who"], "test");
  ::unlink(path.c_str());
}

TEST(AuditLog, AFullDiskIsCountedNotIgnored) {
  // /dev/full accepts open() and fails every write with ENOSPC: a full disk on demand.
  JsonLinesAuditLog log{"/dev/full"};
  ASSERT_TRUE(log.is_open());
  log.append(record("lost"));
  log.append(record("lost too"));
  EXPECT_EQ(log.failed_writes(), 2U);
}

TEST(AuditLog, AnUnopenablePathIsReported) {
  const JsonLinesAuditLog log{"/nonexistent-directory/audit.jsonl"};
  EXPECT_FALSE(log.is_open());
}
