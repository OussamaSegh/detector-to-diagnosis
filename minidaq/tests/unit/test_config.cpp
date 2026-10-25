// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <cstdint>
#include <fstream>
#include <functional>
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
  const auto c = parse_config(R"({"schema_version": "1.3"})");
  ASSERT_TRUE(c) << format_errors(c.error());
  EXPECT_EQ(*c, AcquisitionConfig{});
  // An older minor version is accepted; only the recorded version differs.
  const auto old = parse_config(R"({"schema_version": "1.0"})");
  ASSERT_TRUE(old);
  EXPECT_EQ(old->schema_minor, 0);
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
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "1.4"})"), "/schema_version", "newer MiniDAQ"));
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
  // REQ: SRS-CFG-004
  const auto e = errors_of(R"({
    "schema_version": "1.0",
    "source": {"rate_hz": "fast", "pair_fraction": 1.5, "type": "tcp", "seed": -1},
    "pipeline": {"batch_size": 0, "batches_per_channel": 2.5, "overflow": "ignore"},
    "stop_after_s": -1
  })");
  EXPECT_EQ(e.size(), 8U) << format_errors(e);
  EXPECT_TRUE(has(e, "/source/rate_hz", "must be a number"));
  EXPECT_TRUE(has(e, "/source/pair_fraction", "between 0.0 and 1.0"));
  EXPECT_TRUE(has(e, "/source/type", "must be one of \"synthetic\", \"udp\""));
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
  EXPECT_EQ(p.sorter.window, Picoseconds{3000});
  EXPECT_EQ(p.sorter.delay, Picoseconds{100'000});
  EXPECT_EQ(p.sorter.multiples, MultiplesPolicy::kill_all);
  EXPECT_EQ(p.max_batch_delay, std::chrono::microseconds{250});
  EXPECT_EQ(p.total_words, 3'000'000U);
}

// The JSON Schema in docs/ is documentation for people and other tools; the
// C++ reader is the authority. This test keeps the two from drifting apart.
TEST(Config, SchemaDocumentAgreesWithTheReader) {
  const auto schema = nlohmann::json::parse(read(MINIDAQ_SOURCE_DIR "/docs/architecture/acquisition-config.schema.json"));
  const auto effective = to_json(AcquisitionConfig{});
  const auto base = nlohmann::json::parse(R"({"schema_version": "1.3"})");

  // Walks the schema and the effective configuration together, at any depth:
  // the same keys at every level, and every leaf's enum and range accepted
  // exactly as the schema says.
  std::function<void(const nlohmann::json&, const nlohmann::json&, const std::string&)> check;
  check = [&](const nlohmann::json& props, const nlohmann::json& eff, const std::string& at) {
    ASSERT_EQ(props.size(), eff.size()) << "same keys at '" << at << "'";
    for (const auto& [key, spec] : props.items()) {
      const std::string path = at + "/" + key;
      SCOPED_TRACE(path);
      ASSERT_TRUE(eff.contains(key));
      if (spec.value("type", "") == "object") {
        check(spec["properties"], eff[key], path);
        continue;
      }
      auto with = [&](const nlohmann::json& v) {
        auto doc = base;
        // The energy window's ends are checked against each other: open the
        // other end fully so that each end's own range is what is tested.
        if (path == "/sorter/energy_low_kev") {
          doc["sorter"]["energy_high_kev"] = 10'000.0;
        } else if (path == "/sorter/energy_high_kev") {
          doc["sorter"]["energy_low_kev"] = 0.0;
        } else if (path == "/pipeline/coincidence_window_ps") {
          doc["sorter"]["delay_ps"] = 0;  // the delay must exceed the window
        }
        doc[nlohmann::json::json_pointer{path}] = v;
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
  };
  check(schema["properties"], effective, "");
}

TEST(Config, UdpSource) {
  // REQ: SRS-CFG-010
  const auto c = parse_config(R"({"schema_version": "1.1",
      "source": {"type": "udp", "udp": {"address": "0.0.0.0", "port": 9000, "reorder_window_packets": 128}}})");
  ASSERT_TRUE(c) << format_errors(c.error());
  EXPECT_EQ(c->source.type, "udp");
  EXPECT_EQ(c->source.udp.address, "0.0.0.0");
  EXPECT_EQ(c->source.udp.port, 9000);
  EXPECT_EQ(c->source.udp.reorder_window_packets, 128U);
  EXPECT_EQ(c->source.udp.max_hold_us, 1000);  // default
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "1.1", "source": {"udp": {"reorder_window_packets": 100}}})"),
                  "/source/udp/reorder_window_packets", "power of two"));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "1.1", "source": {"udp": {"port": 70000}}})"), "/source/udp/port",
                  "between 0 and 65535"));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "1.1", "stop_after_s": 2, "source": {"type": "udp"}})"),
                  "/stop_after_s", "synthetic"));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "1.1", "source": {"udp": {"prot": 1}}})"), "/source/udp/prot",
                  "did you mean \"port\""));
}

TEST(Config, SorterSettings) {
  // REQ: SRS-CFG-011
  const auto c = parse_config(R"({"schema_version": "1.2", "pipeline": {"coincidence_window_ps": 3000},
      "sorter": {"delay_ps": 50000, "mode": "per_single", "multiples": "take_winner_of_goods",
                 "energy_low_kev": 400, "energy_high_kev": 650, "min_sector_difference": 2, "fov_radius_mm": 125}})");
  ASSERT_TRUE(c) << format_errors(c.error());
  const PipelineConfig p = to_pipeline_config(*c);
  EXPECT_EQ(p.sorter.window, Picoseconds{3000});
  EXPECT_EQ(p.sorter.delay, Picoseconds{50'000});
  EXPECT_EQ(p.sorter.mode, WindowMode::per_single);
  EXPECT_EQ(p.sorter.multiples, MultiplesPolicy::take_winner_of_goods);
  EXPECT_EQ(p.sorter.energy_low_kev, 400.0);
  EXPECT_EQ(p.sorter.min_sector_difference, 2U);
  EXPECT_EQ(p.sorter.fov_radius_mm, 125.0);
  EXPECT_TRUE(validate(p.sorter)) << "every configuration the parser accepts is a valid sorter";
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "1.2", "sorter": {"delay_ps": 2000}})"), "/sorter/delay_ps",
                  "coincidence_window_ps"));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "1.2", "sorter": {"energy_low_kev": 600}})"),
                  "/sorter/energy_low_kev", "must not exceed"));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "1.2", "sorter": {"multiples": "keep_all"}})"), "/sorter/multiples",
                  "take_all_goods"));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "1.2", "sorter": {"min_sector_difference": 4294967297}})"),
                  "/sorter/min_sector_difference", "between 0 and 12"))
      << "2^32 + 1 must not wrap to 1";
  EXPECT_TRUE(parse_config(R"({"schema_version": "1.2", "sorter": {"delay_ps": 0}})")) << "0 turns the delayed window off";
}

TEST(Config, OutputSettings) {
  // REQ: SRS-CFG-012
  const auto c = parse_config(R"({"schema_version": "1.3", "output": {"type": "listmode", "directory": "/data/run",
      "prefix": "pet", "max_file_mb": 256, "fsync": "interval", "fsync_every_blocks": 32,
      "records_per_block": 1024, "buffers": 8, "max_block_delay_ms": 20}})");
  ASSERT_TRUE(c) << format_errors(c.error());
  EXPECT_EQ(c->output.type, "listmode");
  EXPECT_EQ(c->output.directory, "/data/run");
  EXPECT_EQ(c->output.max_file_mb, 256U);
  EXPECT_EQ(c->output.fsync, "interval");
  EXPECT_EQ(c->output.records_per_block, 1024U);
  EXPECT_EQ(AcquisitionConfig{}.output.type, "none") << "without an output section nothing is written, as before 1.3";
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "1.3", "output": {"fsync": "always"}})"), "/output/fsync",
                  "\"interval\""));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "1.3", "output": {"prefix": "a/b"}})"), "/output/prefix", "'/'"));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "1.3", "output": {"directory": ""}})"), "/output/directory",
                  "must not be empty"));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "1.3", "output": {"records_per_block": 4294967297}})"),
                  "/output/records_per_block", "between 1 and 65536"))
      << "2^32 + 1 must not wrap to 1";
}

TEST(Config, NumberOverflowIsAnErrorNotACrash) {
  // Regression: fuzz/fuzz_config found that "6e688" escaped parse_config as an
  // nlohmann out_of_range exception and terminated the program.
  for (const char* text : {"6e688", R"({"schema_version": "1.0", "source": {"rate_hz": 1e999}})"}) {
    const auto r = parse_config(text);
    ASSERT_FALSE(r.has_value()) << text;
    ASSERT_EQ(r.error().size(), 1U);
    EXPECT_NE(r.error()[0].message.find("number overflow"), std::string::npos) << r.error()[0].message;
  }
}
