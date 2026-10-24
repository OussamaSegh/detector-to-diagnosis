// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <cstdint>
#include <fstream>
#include <sstream>

#include <nlohmann/json.hpp>

#include "minidaq/config/acquisition_config.hpp"

using namespace minidaq;
using namespace minidaq::config;

namespace {
ConfigErrors errors_of(std::string_view text) {
  auto r = parse_config(text);
  return r ? ConfigErrors{} : r.error();
}
bool has(const ConfigErrors& e, std::string_view path, std::string_view text) {
  for (const auto& x : e) {
    if (x.path == path && x.message.find(text) != std::string::npos) {
      return true;
    }
  }
  return false;
}
std::string read(const std::string& path) {
  std::ifstream in{path};
  std::stringstream s;
  s << in.rdbuf();
  return s.str();
}
}  // namespace

TEST(Config, MinimalDocumentGetsDefaults) {
  // REQ: SRS-CFG-001
  const auto c = parse_config(R"({"schema_version": "1.0"})");
  ASSERT_TRUE(c) << format_errors(c.error());
  EXPECT_EQ(*c, AcquisitionConfig{});
}

TEST(Config, ShippedConfigurationsAreValid) {
  for (const char* f : {"default.json", "short-run.json"}) {
    const auto c = parse_config(read(std::string{MINIDAQ_SOURCE_DIR "/minidaq/configs/"} + f));
    EXPECT_TRUE(c) << f << ":\n" << (c ? "" : format_errors(c.error()));
  }
}

TEST(Config, EffectiveConfigurationRoundTrips) {
  AcquisitionConfig c;
  c.description = "round trip";
  c.source.rate_hz = 2.5e6;
  c.source.seed = 42;
  c.pipeline.batch_size = 512;
  c.pipeline.overflow = OverflowPolicy::drop;
  c.stop_after_s = 3.5;
  const auto back = config_from_json(to_json(c));
  ASSERT_TRUE(back) << format_errors(back.error());
  EXPECT_EQ(*back, c);
}

TEST(Config, SchemaVersionRules) {
  // REQ: SRS-CFG-002
  EXPECT_TRUE(has(errors_of(R"({})"), "/schema_version", "is required"));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "2.0"})"), "/schema_version", "major version 2"));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "1.1"})"), "/schema_version", "newer MiniDAQ"));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "1"})"), "/schema_version", "must look like"));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": 1.0})"), "/schema_version", "must be a string"));
}

TEST(Config, UnknownKeysAreErrorsWithSuggestions) {
  // REQ: SRS-CFG-003
  const auto e = errors_of(R"({"schema_version": "1.0", "pipeline": {"batchsize": 512}, "colour": 1})");
  EXPECT_TRUE(has(e, "/pipeline/batchsize", "did you mean \"batch_size\"")) << format_errors(e);
  EXPECT_TRUE(has(e, "/colour", "unknown key"));
  EXPECT_FALSE(has(e, "/colour", "did you mean")) << "no suggestion when nothing is close";
}

TEST(Config, TypesAndRangesAreCheckedAndAllErrorsReported) {
  const auto e = errors_of(R"({
    "schema_version": "1.0",
    "source": {"rate_hz": "fast", "pair_fraction": 1.5, "type": "udp", "seed": -1},
    "pipeline": {"batch_size": 0, "batches_per_channel": 2.5, "overflow": "ignore"},
    "stop_after_s": -1
  })");
  EXPECT_EQ(e.size(), 8U) << format_errors(e);
  EXPECT_TRUE(has(e, "/source/rate_hz", "must be a number"));
  EXPECT_TRUE(has(e, "/source/pair_fraction", "between 0.0 and 1.0"));
  EXPECT_TRUE(has(e, "/source/type", "must be one of \"synthetic\""));
  EXPECT_TRUE(has(e, "/source/seed", "non-negative integer"));
  EXPECT_TRUE(has(e, "/pipeline/batch_size", "between 1 and 1048576"));
  EXPECT_TRUE(has(e, "/pipeline/batches_per_channel", "non-negative integer"));
  EXPECT_TRUE(has(e, "/pipeline/overflow", "\"block\", \"drop\""));
  EXPECT_TRUE(has(e, "/stop_after_s", "between"));
}

TEST(Config, SyntaxErrorsAndWrongDocumentTypes) {
  const auto e = errors_of(R"({"schema_version": "1.0",)");
  ASSERT_EQ(e.size(), 1U);
  EXPECT_NE(e[0].message.find("not valid JSON"), std::string::npos);
  EXPECT_TRUE(has(errors_of("[1, 2]"), "", "must be an object"));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "1.0", "source": 3})"), "/source", "must be an object"));
}

TEST(Config, CommentsAreAllowed) {
  // Operators annotate configuration files; JSON has no comments, the parser allows them.
  EXPECT_TRUE(parse_config("// site A\n{\"schema_version\": \"1.0\" /* v1 */}"));
}

TEST(Config, PipelineSettingsAreApplied) {
  AcquisitionConfig c;
  c.pipeline.batch_size = 1024;
  c.pipeline.coincidence_window_ps = 3000;
  c.pipeline.max_batch_delay_us = 250;
  c.source.rate_hz = 2e6;
  c.stop_after_s = 1.5;
  const PipelineConfig p = to_pipeline_config(c);
  EXPECT_EQ(p.batch_size, 1024U);
  EXPECT_EQ(p.coincidence_window, Picoseconds{3000});
  EXPECT_EQ(p.max_batch_delay, std::chrono::microseconds{250});
  EXPECT_EQ(p.total_words, 3'000'000U);
}

// The JSON Schema in docs/ is documentation for people and other tools; the
// C++ reader is the authority. This test keeps the two from drifting apart.
TEST(Config, SchemaDocumentAgreesWithTheReader) {
  const auto schema = nlohmann::json::parse(read(MINIDAQ_SOURCE_DIR "/docs/architecture/acquisition-config.schema.json"));
  const auto effective = to_json(AcquisitionConfig{});
  const auto base = nlohmann::json::parse(R"({"schema_version": "1.0"})");

  ASSERT_EQ(schema["properties"].size(), effective.size()) << "same top-level keys";
  for (const auto& [key, prop] : schema["properties"].items()) {
    ASSERT_TRUE(effective.contains(key)) << key;
    const bool object = prop.value("type", "") == "object";
    if (object) {
      EXPECT_EQ(prop["properties"].size(), effective[key].size()) << key;
    }
    const auto leaves = object ? prop["properties"] : nlohmann::json{{key, prop}};
    for (const auto& [leaf, spec] : leaves.items()) {
      const nlohmann::json::json_pointer ptr{object ? "/" + key + "/" + leaf : "/" + key};
      SCOPED_TRACE(ptr.to_string());
      if (object) {
        ASSERT_TRUE(effective[key].contains(leaf));
      }
      auto with = [&](const nlohmann::json& v) {
        auto doc = base;
        doc[ptr] = v;
        return parse_config(doc.dump()).has_value();
      };
      if (spec.contains("enum")) {
        for (const auto& v : spec["enum"]) {
          EXPECT_TRUE(with(v)) << v;
        }
        EXPECT_FALSE(with("not-an-option"));
      }
      const bool integer = spec.value("type", "") == "integer";
      if (spec.contains("minimum")) {
        const double lo = spec["minimum"].get<double>();
        EXPECT_TRUE(integer ? with(spec["minimum"].get<std::int64_t>()) : with(lo));
        EXPECT_FALSE(integer ? with(spec["minimum"].get<std::int64_t>() - 1) : with(lo - 0.5));
      }
      if (spec.contains("maximum") && spec["maximum"].is_number_float()) {
        const double hi = spec["maximum"].get<double>();
        EXPECT_TRUE(with(hi));
        EXPECT_FALSE(with(hi * 1.5));
      } else if (spec.contains("maximum") && spec["maximum"].get<std::uint64_t>() == UINT64_MAX) {
        EXPECT_TRUE(with(UINT64_MAX)) << "the full unsigned range; nothing above it to try";
      } else if (spec.contains("maximum") && spec["maximum"].is_number_integer()) {
        const auto hi = spec["maximum"].get<std::int64_t>();
        EXPECT_TRUE(with(hi));
        EXPECT_FALSE(with(hi + 1));
      }
      if (integer) {
        EXPECT_FALSE(with(1.5)) << "integers only";
      }
    }
  }
}
