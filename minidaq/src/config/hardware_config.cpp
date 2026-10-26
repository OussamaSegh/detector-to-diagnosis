// SPDX-License-Identifier: MIT
#include "minidaq/config/hardware_config.hpp"

#include <cmath>
#include <nlohmann/json.hpp>
#include <set>

#include "object_reader.hpp"

namespace minidaq::config {
namespace {

using detail::json;
using detail::ObjectReader;

void read_board(const json& j, const std::string& at, const std::string& backend, BoardConfig& b,
                ConfigErrors& errors) {
  ObjectReader r{j, at, errors};
  if (backend == "mmio") {
    r.get("device", b.device);
    r.get<std::uint64_t>("offset", b.offset, 0, std::uint64_t{1} << 40);
    r.get<std::uint64_t>("size", b.size, 4, std::uint64_t{1} << 20);
    if (j.is_object() && !j.contains("device")) {
      errors.push_back({at + "/device", "is required"});
    }
  } else {
    r.get<std::uint32_t>("slot", b.slot, 0, 255);
    r.get<double>("temperature_c", b.temperature_c, -40.0, 125.0);
    r.get("temperature_file", b.temperature_file);
    r.get<double>("dark_current_ua", b.dark_current_ua, 0.0, 10'000.0);
    r.get("fault", b.fault, {"none", "unresponsive", "vanished", "weak_supply"});
  }
  r.finish();
}

}  // namespace

Expected<HardwareConfig, ConfigErrors> parse_hardware_config(std::string_view json_text) {
  const json doc = json::parse(json_text, nullptr, false, true);
  if (doc.is_discarded()) {
    return Unexpected{ConfigErrors{{"", "not valid JSON"}}};
  }
  ConfigErrors errors;
  HardwareConfig c;
  hw::SlowControlSettings& s = c.settings;
  ObjectReader top{doc, "", errors};

  std::string version;
  top.get("schema_version", version);
  int major = 0;
  int minor = 0;
  if (doc.is_object() && !doc.contains("schema_version")) {
    errors.push_back({"/schema_version", "is required"});
  } else if (!version.empty() &&
             (!detail::parse_version(version, major, minor) || major != hardware_supported_major ||
              minor > hardware_supported_minor)) {
    errors.push_back(
        {"/schema_version", "must be \"1.0\" (this program reads hardware descriptions 1.0)"});
  }
  top.get("backend", c.backend, {"simulated", "mmio"});
  int period_ms = static_cast<int>(s.period.count());
  top.get<int>("period_ms", period_ms, 10, 10'000);
  s.period = std::chrono::milliseconds{period_ms};
  top.get<int>("max_failed_cycles", s.max_failed_cycles, 1, 100);

  // [snippet:bias]
  if (const json* bias = top.object("bias")) {
    ObjectReader r{*bias, "/bias", errors};
    double vbd_v = s.law.vbd_25c_mv / 1000.0;
    double vov_v = s.law.overvoltage_mv / 1000.0;
    double min_v = s.bias_min_mv / 1000.0;
    double max_v = s.bias_max_mv / 1000.0;
    double ramp_v_per_s = s.ramp_mv_per_s / 1000.0;
    r.get<double>("breakdown_25c_v", vbd_v, 10.0, 80.0);
    r.get<double>("breakdown_mv_per_c", s.law.vbd_mv_per_c, 0.0, 100.0);
    r.get<double>("overvoltage_v", vov_v, 0.5, 15.0);
    r.get<double>("min_v", min_v, 0.0, 100.0);
    r.get<double>("max_v", max_v, 0.0, 100.0);
    r.get<double>("ramp_v_per_s", ramp_v_per_s, 0.01, 1'000.0);
    r.get<double>("update_step_mv", s.update_step_mv, 0.1, 1'000.0);
    r.get<double>("readback_tolerance_mv", s.readback_tolerance_mv, 1.0, 5'000.0);
    int grace_ms = static_cast<int>(s.readback_grace.count());
    r.get<int>("readback_grace_ms", grace_ms, 0, 600'000);
    r.get<double>("max_current_ua", s.max_current_ua, 1.0, 65'535.0);
    r.finish();
    s.law.vbd_25c_mv = vbd_v * 1000.0;
    s.law.overvoltage_mv = vov_v * 1000.0;
    s.bias_min_mv = min_v * 1000.0;
    s.bias_max_mv = max_v * 1000.0;
    s.ramp_mv_per_s = static_cast<std::uint32_t>(std::lround(ramp_v_per_s * 1000.0));
    s.readback_grace = std::chrono::milliseconds{grace_ms};
    if (min_v >= max_v) {
      errors.push_back({"/bias/min_v", "must be below /bias/max_v"});
    }
  }
  // [/snippet:bias]
  if (const json* t = top.object("temperature")) {
    ObjectReader r{*t, "/temperature", errors};
    r.get<double>("warning_c", s.temp_warning_c, -40.0, 125.0);
    r.get<double>("alarm_c", s.temp_alarm_c, -40.0, 125.0);
    r.get<double>("hysteresis_c", s.temp_hysteresis_c, 0.0, 20.0);
    r.get<double>("min_c", s.temp_min_c, -40.0, 125.0);
    r.finish();
    if (s.temp_min_c >= s.temp_warning_c ||
        s.temp_warning_c >= s.temp_alarm_c) {  // values are range-checked, never NaN
      errors.push_back({"/temperature", "must have min_c < warning_c < alarm_c"});
    }
  }

  const json* boards = top.object("boards");
  if (boards == nullptr) {
    errors.push_back({"/boards", "is required"});
  } else if (!boards->is_array() || boards->empty() || boards->size() > max_boards) {
    errors.push_back(
        {"/boards", "must be an array of 1 to " + std::to_string(max_boards) + " boards"});
  } else {
    std::set<std::uint32_t> slots;
    for (std::size_t i = 0; i < boards->size(); ++i) {
      const std::string at = "/boards/" + std::to_string(i);
      BoardConfig b;
      read_board((*boards)[i], at, c.backend, b, errors);
      if (c.backend == "simulated" && !slots.insert(b.slot).second) {
        errors.push_back({at + "/slot", "slot " + std::to_string(b.slot) + " is used twice"});
      }
      c.boards.push_back(std::move(b));
    }
  }
  top.finish();
  if (!errors.empty()) {
    return Unexpected{std::move(errors)};
  }
  return c;
}

}  // namespace minidaq::config
