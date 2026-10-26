// SPDX-License-Identifier: MIT
#include "minidaq/control/run_integrity.hpp"

#include <cstdint>
#include <string>
#include <string_view>

namespace minidaq::control {

namespace {

using nlohmann::json;

// Fails safe: a loss counter that is anything but an integer 0 is a loss, so
// a counter reported with another type cannot hide one.
void add(json& losses, const std::string& pointer, const json& value) {
  const bool zero = (value.is_number_unsigned() && value.get<std::uint64_t>() == 0) ||
                    (value.is_number_integer() && value.get<std::int64_t>() == 0);
  if (!zero) {
    losses.push_back({{"counter", pointer}, {"count", value}});
  }
}

}  // namespace

// [snippet:assess]
json assess_integrity(const json& status) {
  json losses = json::array();
  if (const auto it = status.find("detector_counters"); it != status.end() && it->is_object()) {
    for (const auto& [name, value] : it->items()) {
      if (name == "packets_lost" || name == "sequence_resyncs" || name == "socket_drops" ||
          std::string_view{name}.starts_with("rejected_")) {
        add(losses, "/detector_counters/" + name, value);
      }
    }
  }
  if (const auto it = status.find("stages"); it != status.end() && it->is_array()) {
    for (std::size_t i = 0; i < it->size(); ++i) {
      const json& stage = (*it)[i];
      const std::string at = "/stages/" + std::to_string(i);
      add(losses, at + "/dropped", stage.value("dropped", json(0U)));
      if (stage.value("name", "") == "decode") {  // words that decode to no valid single
        add(losses, at + "/filtered", stage.value("filtered", json(0U)));
      }
    }
  }
  add(losses, "/late_singles", status.value("late_singles", json(0U)));
  if (const auto it = status.find("sorter"); it != status.end() && it->is_object()) {
    add(losses, "/sorter/out_of_order", it->value("out_of_order", json(0U)));
  }
  if (const auto it = status.find("sink_counters"); it != status.end() && it->is_object()) {
    for (const char* name : {"invalid", "energies_clamped", "blocks_dropped"}) {
      add(losses, std::string{"/sink_counters/"} + name, it->value(name, json(0U)));
    }
  }
  const bool fault = status.contains("fault") && !status["fault"].is_null();
  return {{"complete", !fault && losses.empty()}, {"losses", std::move(losses)}};
}
// [/snippet:assess]

}  // namespace minidaq::control
