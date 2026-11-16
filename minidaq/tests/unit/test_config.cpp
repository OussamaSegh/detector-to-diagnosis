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
  const auto c = parse_config(R"({"schema_version": "2.1", "source": {"type": "synthetic"}})");
  ASSERT_TRUE(c) << format_errors(c.error());
  EXPECT_EQ(*c, AcquisitionConfig{});
}

TEST(Config, TheSourceIsNeverADefault) {
  // REQ: SRS-CFG-013
  // 2.0 (CR-0030): 1.x took a forgotten source to be the simulator (H-06).
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "2.0"})"), "/source", "is required"));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "2.0", "source": {"rate_hz": 1000}})"),
                  "/source/type", "is required"));
}

TEST(Config, AVersion1FileIsRefusedWithTheWayToConvertIt) {
  // REQ: SRS-CFG-014
  for (const char* v : {"1.0", "1.4"}) {
    const auto e = errors_of(std::string{R"({"schema_version": ")"} + v +
                             R"(", "source": {"type": "synthetic"}})");
    EXPECT_TRUE(has(e, "/schema_version", "major version 1")) << v;
    EXPECT_TRUE(has(e, "/schema_version", "tools/migrate_config.py"))
        << v << ": " << format_errors(e);
  }
}

TEST(Config, RenamedFieldsAreUnknownInTheirOldPlaces) {
  // REQ: SRS-CFG-014
  const auto e =
      errors_of(R"({"schema_version": "2.0", "source": {"type": "synthetic"}, "stop_after_s": 1,
      "rt_profile": "rt.json", "pipeline": {"coincidence_window_ps": 3000}, "output": {"max_file_mb": 4}})");
  EXPECT_TRUE(has(e, "/stop_after_s", "unknown key")) << format_errors(e);
  EXPECT_TRUE(has(e, "/rt_profile", "unknown key"));
  EXPECT_TRUE(has(e, "/pipeline/coincidence_window_ps", "unknown key"));
  EXPECT_TRUE(has(e, "/output/max_file_mb", "did you mean \"max_file_mib\""));
}

TEST(Config, TheTimingMonitorIsReadFromSchema21) {
  // REQ: SRS-CFG-016
  const auto c = parse_config(R"({"schema_version": "2.1", "source": {"type": "synthetic"},
      "timing_monitor": {"interval_s": 0.5, "baseline_intervals": 4, "min_trues": 20,
      "half_window_ps": 1500, "warning_ps": 80, "alarm_ps": 200, "significance": 4}})");
  ASSERT_TRUE(c) << format_errors(c.error());
  const auto p = minidaq::config::to_pipeline_config(*c);
  EXPECT_EQ(p.timing.interval, Picoseconds{500'000'000'000});
  EXPECT_EQ(p.timing.baseline_intervals, 4U);
  EXPECT_EQ(p.timing.min_trues, 20.0);
  EXPECT_EQ(p.timing.half_window, Picoseconds{1'500});
  EXPECT_EQ(p.timing.warning_ps, 80.0);
  EXPECT_EQ(p.timing.alarm_ps, 200.0);
  EXPECT_EQ(p.timing.significance, 4.0);
  EXPECT_TRUE(minidaq::validate(p.timing).has_value());
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "2.1", "source": {"type": "synthetic"},
      "timing_monitor": {"warning_ps": 300, "alarm_ps": 200}})"),
                  "/timing_monitor/alarm_ps", "must not be below"));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "2.1", "source": {"type": "synthetic"},
      "timing_monitor": {"interval": 1}})"),
                  "/timing_monitor/interval", "unknown key"));
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
  c.source.stop_after_s = 3.5;
  const auto back = config_from_json(to_json(c));
  ASSERT_TRUE(back) << format_errors(back.error());
  EXPECT_EQ(*back, c);
}

TEST(Config, SchemaVersionRules) {
  // REQ: SRS-CFG-002
  EXPECT_TRUE(has(errors_of(R"({})"), "/schema_version", "is required"));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "3.0"})"), "/schema_version", "major version 3"));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "2.2"})"), "/schema_version", "newer MiniDAQ"));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": ""})"), "/schema_version", "must look like"))
      << "an empty version is not a version (MDQ-PR-042)";
  EXPECT_TRUE(has(errors_of(R"({"schema_version": "1"})"), "/schema_version", "must look like"));
  EXPECT_TRUE(has(errors_of(R"({"schema_version": 1.0})"), "/schema_version", "must be a string"));
}

TEST(Config, UnknownKeysAreErrorsWithSuggestions) {
  // REQ: SRS-CFG-003
  const auto e = errors_of(
      R"({"schema_version": "2.0", "source": {"type": "synthetic"}, "pipeline": {"batchsize": 512}, "colour": 1})");
  EXPECT_TRUE(has(e, "/pipeline/batchsize", "did you mean \"batch_size\"")) << format_errors(e);
  EXPECT_TRUE(has(e, "/colour", "unknown key"));
  EXPECT_FALSE(has(e, "/colour", "did you mean")) << "no suggestion when nothing is close";
}

TEST(Config, TypesAndRangesAreCheckedAndAllErrorsReported) {
  // REQ: SRS-CFG-004
  const auto e = errors_of(R"({
    "schema_version": "2.0",
    "source": {"rate_hz": "fast", "pair_fraction": 1.5, "type": "tcp", "seed": -1, "stop_after_s": -1},
    "pipeline": {"batch_size": 0, "batches_per_channel": 2.5, "overflow": "ignore"}
  })");
  EXPECT_EQ(e.size(), 8U) << format_errors(e);
  EXPECT_TRUE(has(e, "/source/rate_hz", "must be a number"));
  EXPECT_TRUE(has(e, "/source/pair_fraction", "between 0.0 and 1.0"));
  EXPECT_TRUE(has(e, "/source/type", "must be one of \"synthetic\", \"udp\""));
  EXPECT_TRUE(has(e, "/source/seed", "non-negative integer"));
  EXPECT_TRUE(has(e, "/pipeline/batch_size", "between 1 and 1048576"));
  EXPECT_TRUE(has(e, "/pipeline/batches_per_channel", "non-negative integer"));
  EXPECT_TRUE(has(e, "/pipeline/overflow", "\"block\", \"drop\""));
  EXPECT_TRUE(has(e, "/source/stop_after_s", "between"));
}

TEST(Config, SyntaxErrorsAndWrongDocumentTypes) {
  const auto e = errors_of(R"({"schema_version": "2.0",)");
  ASSERT_EQ(e.size(), 1U);
  EXPECT_NE(e[0].message.find("not valid JSON"), std::string::npos);
  EXPECT_TRUE(has(errors_of("[1, 2]"), "", "must be an object"));
  EXPECT_TRUE(
      has(errors_of(R"({"schema_version": "2.0", "source": 3})"), "/source", "must be an object"));
}

TEST(Config, CommentsAreAllowed) {
  // Operators annotate configuration files; JSON has no comments, the parser allows them.
  EXPECT_TRUE(parse_config(
      "// site A\n{\"schema_version\": \"2.0\" /* v2 */, \"source\": {\"type\": \"udp\"}}"));
}

TEST(Config, PipelineSettingsAreApplied) {
  AcquisitionConfig c;
  c.pipeline.batch_size = 1024;
  c.sorter.window_ps = 3000;
  c.pipeline.max_batch_delay_us = 250;
  c.source.rate_hz = 2e6;
  c.source.stop_after_s = 1.5;
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
  const auto base =
      nlohmann::json::parse(R"({"schema_version": "2.0", "source": {"type": "synthetic"}})");

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
        } else if (path == "/sorter/window_ps") {
          doc["sorter"]["delay_ps"] = 0;  // the delay must exceed the window
        } else if (path == "/timing_monitor/warning_ps") {
          doc["timing_monitor"]["alarm_ps"] = 1e6;  // the alarm must not be below the warning
        } else if (path == "/timing_monitor/alarm_ps") {
          doc["timing_monitor"]["warning_ps"] = 1.0;
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
  const auto c = parse_config(R"({"schema_version": "2.0",
      "source": {"type": "udp", "udp": {"address": "0.0.0.0", "port": 9000, "reorder_window_packets": 128}}})");
  ASSERT_TRUE(c) << format_errors(c.error());
  EXPECT_EQ(c->source.type, "udp");
  EXPECT_EQ(c->source.udp.address, "0.0.0.0");
  EXPECT_EQ(c->source.udp.port, 9000);
  EXPECT_EQ(c->source.udp.reorder_window_packets, 128U);
  EXPECT_EQ(c->source.udp.max_hold_us, 1000);  // default
  EXPECT_TRUE(has(
      errors_of(
          R"({"schema_version": "2.0", "source": {"type": "udp", "udp": {"reorder_window_packets": 100}}})"),
      "/source/udp/reorder_window_packets", "power of two"));
  EXPECT_TRUE(has(
      errors_of(R"({"schema_version": "2.0", "source": {"type": "udp", "udp": {"port": 70000}}})"),
      "/source/udp/port", "between 0 and 65535"));
  EXPECT_TRUE(
      has(errors_of(R"({"schema_version": "2.0", "source": {"type": "udp", "stop_after_s": 2}})"),
          "/source/stop_after_s", "synthetic"));
  EXPECT_TRUE(
      has(errors_of(R"({"schema_version": "2.0", "source": {"type": "udp", "udp": {"prot": 1}}})"),
          "/source/udp/prot", "did you mean \"port\""));
}

TEST(Config, SorterSettings) {
  // REQ: SRS-CFG-011
  const auto c = parse_config(R"({"schema_version": "2.0", "source": {"type": "synthetic"},
      "sorter": {"window_ps": 3000, "delay_ps": 50000, "mode": "per_single", "multiples": "take_winner_of_goods",
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
  EXPECT_TRUE(has(
      errors_of(
          R"({"schema_version": "2.0", "source": {"type": "synthetic"}, "sorter": {"delay_ps": 2000}})"),
      "/sorter/delay_ps", "window_ps"));
  EXPECT_TRUE(has(
      errors_of(
          R"({"schema_version": "2.0", "source": {"type": "synthetic"}, "sorter": {"energy_low_kev": 600}})"),
      "/sorter/energy_low_kev", "must not exceed"));
  EXPECT_TRUE(has(
      errors_of(
          R"({"schema_version": "2.0", "source": {"type": "synthetic"}, "sorter": {"multiples": "keep_all"}})"),
      "/sorter/multiples", "take_all_goods"));
  EXPECT_TRUE(has(
      errors_of(
          R"({"schema_version": "2.0", "source": {"type": "synthetic"}, "sorter": {"min_sector_difference": 4294967297}})"),
      "/sorter/min_sector_difference", "between 0 and 12"))
      << "2^32 + 1 must not wrap to 1";
  EXPECT_TRUE(parse_config(
      R"({"schema_version": "2.0", "source": {"type": "synthetic"}, "sorter": {"delay_ps": 0}})"))
      << "0 turns the delayed window off";
}

TEST(Config, OutputSettings) {
  // REQ: SRS-CFG-012
  const auto c = parse_config(
      R"({"schema_version": "2.0", "source": {"type": "synthetic"}, "output": {"type": "listmode",
      "directory": "/data/run", "prefix": "pet", "max_file_mib": 256, "fsync": "interval", "fsync_every_blocks": 32,
      "records_per_block": 1024, "buffers": 8, "max_block_delay_ms": 20}})");
  ASSERT_TRUE(c) << format_errors(c.error());
  EXPECT_EQ(c->output.type, "listmode");
  EXPECT_EQ(c->output.directory, "/data/run");
  EXPECT_EQ(c->output.max_file_mib, 256U);
  EXPECT_EQ(c->output.fsync, "interval");
  EXPECT_EQ(c->output.records_per_block, 1024U);
  EXPECT_EQ(AcquisitionConfig{}.output.type, "none")
      << "without an output section nothing is written";
  EXPECT_TRUE(has(
      errors_of(
          R"({"schema_version": "2.0", "source": {"type": "synthetic"}, "output": {"fsync": "always"}})"),
      "/output/fsync", "\"interval\""));
  EXPECT_TRUE(has(
      errors_of(
          R"({"schema_version": "2.0", "source": {"type": "synthetic"}, "output": {"prefix": "a/b"}})"),
      "/output/prefix", "'/'"));
  EXPECT_TRUE(has(
      errors_of(
          R"({"schema_version": "2.0", "source": {"type": "synthetic"}, "output": {"directory": ""}})"),
      "/output/directory", "must not be empty"));
  EXPECT_TRUE(has(
      errors_of(
          R"({"schema_version": "2.0", "source": {"type": "synthetic"}, "output": {"records_per_block": 4294967297}})"),
      "/output/records_per_block", "between 1 and 65536"))
      << "2^32 + 1 must not wrap to 1";
}

TEST(Config, NumberOverflowIsAnErrorNotACrash) {
  // Regression: fuzz/fuzz_config found that "6e688" escaped parse_config as an
  // nlohmann out_of_range exception and terminated the program.
  for (const char* text :
       {"6e688",
        R"({"schema_version": "2.0", "source": {"type": "synthetic", "rate_hz": 1e999}})"}) {
    const auto r = parse_config(text);
    ASSERT_FALSE(r.has_value()) << text;
    ASSERT_EQ(r.error().size(), 1U);
    EXPECT_NE(r.error()[0].message.find("number overflow"), std::string::npos) << r.error()[0].message;
  }
}
