// SPDX-License-Identifier: MIT
// MiniDAQ - acquisition configuration: a versioned, validated JSON document
// (Chapter 6).
//
// A configuration file is an input from outside the program, so it is parsed
// strictly: every key is known, every value has the right type and range,
// and all problems are reported at once, each with the JSON Pointer of the
// value at fault ("/pipeline/batch_size: must be between 1 and 1048576").
// Unknown keys are errors, with a suggestion when one is close to a known
// key: a typo must never silently become a default.
//
// Versioning: "schema_version" is "MAJOR.MINOR". A different major version is
// rejected. A newer minor version is rejected too, because it may contain
// keys this program does not understand; an older minor version is accepted
// (new keys only ever get defaults). The JSON Schema for external tools is
// docs/architecture/acquisition-config.schema.json.
#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include <nlohmann/json_fwd.hpp>

#include "minidaq/core/expected.hpp"
#include "minidaq/pipeline/acquisition_pipeline.hpp"

namespace minidaq::config {

inline constexpr int supported_major = 1;
inline constexpr int supported_minor = 1;  // 1.1: source type "udp" (Chapter 9)

// The UDP readout link (Chapter 9, minidaq/control/udp_detector.hpp).
struct UdpSettings {
  std::string address = "127.0.0.1";  // IPv4 address to listen on
  std::uint16_t port = 7701;           // 0: any free port (tests)
  std::size_t receive_buffer_bytes = std::size_t{8} << 20;
  std::size_t reorder_window_packets = 64;  // a power of two
  std::int64_t max_hold_us = 1'000;         // a gap older than this is declared lost
  friend bool operator==(const UdpSettings&, const UdpSettings&) = default;
};

struct SourceSettings {
  std::string type = "synthetic";  // "synthetic" or "udp"
  double rate_hz = 10e6;           // synthetic: singles per second
  double pair_fraction = 0.3;      // synthetic
  std::uint64_t seed = 1;          // synthetic
  UdpSettings udp;                 // udp
  friend bool operator==(const SourceSettings&, const SourceSettings&) = default;
};

struct PipelineSettings {
  std::size_t batch_size = 4096;
  std::size_t batches_per_channel = 64;
  std::int64_t coincidence_window_ps = 4'000;
  OverflowPolicy overflow = OverflowPolicy::block;
  std::int64_t max_batch_delay_us = 500;
  friend bool operator==(const PipelineSettings&, const PipelineSettings&) = default;
};

struct AcquisitionConfig {
  int schema_major = supported_major;
  int schema_minor = supported_minor;
  std::string description;
  SourceSettings source;
  PipelineSettings pipeline;
  std::string rt_profile;   // path of a real-time profile file (Chapter 4); empty: none
  double stop_after_s = 0;  // 0: run until stopped

  friend bool operator==(const AcquisitionConfig&, const AcquisitionConfig&) = default;
};

struct ConfigError {
  std::string path;  // JSON Pointer of the offending value ("" for the document)
  std::string message;
  friend bool operator==(const ConfigError&, const ConfigError&) = default;
};
using ConfigErrors = std::vector<ConfigError>;

[[nodiscard]] Expected<AcquisitionConfig, ConfigErrors> parse_config(std::string_view json_text);
[[nodiscard]] Expected<AcquisitionConfig, ConfigErrors> config_from_json(const nlohmann::json& doc);
// The effective configuration, defaults included: what an acquisition records
// next to its data so that the run can be reproduced.
[[nodiscard]] nlohmann::json to_json(const AcquisitionConfig& c);
[[nodiscard]] std::string format_errors(const ConfigErrors& errors);

// The pipeline part of the configuration (the real-time profile is applied by
// the caller, which reads the profile file).
[[nodiscard]] PipelineConfig to_pipeline_config(const AcquisitionConfig& c);

}  // namespace minidaq::config
