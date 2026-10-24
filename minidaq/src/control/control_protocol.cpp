// SPDX-License-Identifier: MIT
#include "minidaq/control/control_protocol.hpp"

#include <nlohmann/json.hpp>

#include "minidaq/config/acquisition_config.hpp"

#ifndef MINIDAQ_VERSION_STRING
#define MINIDAQ_VERSION_STRING "unknown"
#endif

namespace minidaq::control {

using nlohmann::json;

std::optional<std::string> LineFramer::next() {
  if (overflowed_) {
    return std::nullopt;
  }
  const std::size_t nl = buffer_.find('\n', scanned_);
  if (nl == std::string::npos) {
    scanned_ = buffer_.size();
    if (buffer_.size() > max_line_) {
      overflowed_ = true;
      buffer_.clear();
    }
    return std::nullopt;
  }
  if (nl > max_line_) {
    overflowed_ = true;
    buffer_.clear();
    return std::nullopt;
  }
  std::string line = buffer_.substr(0, nl);
  buffer_.erase(0, nl + 1);
  scanned_ = 0;
  if (!line.empty() && line.back() == '\r') {
    line.pop_back();
  }
  return line;
}

namespace {

json error_response(const json& id, AcqState state, std::string_view code, std::string_view message) {
  return json{{"api", api_version},
              {"id", id},
              {"ok", false},
              {"state", to_string(state)},
              {"error", {{"code", code}, {"message", message}}}};
}

json command_response(const json& id, const CommandResult& r) {
  if (!r.ok) {
    return error_response(id, r.state, r.code, r.message);
  }
  return json{{"api", api_version}, {"id", id}, {"ok", true}, {"state", to_string(r.state)}};
}

bool major_matches(const std::string& v) {
  const std::string want{api_version.substr(0, api_version.find('.'))};
  return v.substr(0, v.find('.')) == want;
}

std::string dump(const json& j) { return j.dump(-1, ' ', false, json::error_handler_t::replace); }

}  // namespace

// [snippet:handle]
std::string handle_request(std::string_view line, AcquisitionService& service, std::string_view who) {
  const json req = json::parse(line, nullptr, /*allow_exceptions=*/false);
  if (req.is_discarded() || !req.is_object()) {
    return dump(error_response(nullptr, service.state(), "bad_request", "a request is one JSON object per line"));
  }
  const json id = req.contains("id") ? req["id"] : json(nullptr);
  if (req.contains("api") && (!req["api"].is_string() || !major_matches(req["api"].get<std::string>()))) {
    return dump(error_response(id, service.state(), "unsupported_api",
                               "this server speaks API " + std::string{api_version}));
  }
  if (!req.contains("cmd") || !req["cmd"].is_string()) {
    return dump(error_response(id, service.state(), "bad_request", "missing \"cmd\""));
  }
  const auto& cmd = req["cmd"].get_ref<const std::string&>();
  if (cmd == "hello") {
    return dump(json{{"api", api_version},
                     {"id", id},
                     {"ok", true},
                     {"server", std::string{"minidaq "} + MINIDAQ_VERSION_STRING},
                     {"commands", {"hello", "configure", "start", "stop", "reset", "status"}}});
  }
  if (cmd == "status") {
    return dump(json{{"api", api_version}, {"id", id}, {"ok", true}, {"status", service.status()}});
  }
  if (cmd == "configure") {
    if (!req.contains("config")) {
      return dump(error_response(id, service.state(), "bad_request", "configure needs \"config\""));
    }
    auto cfg = config::config_from_json(req["config"]);
    if (!cfg) {
      json details = json::array();
      for (const auto& e : cfg.error()) {
        details.push_back({{"path", e.path}, {"message", e.message}});
      }
      service.note(who, "configure", "rejected: invalid configuration", false);
      json r = error_response(id, service.state(), "config_error", config::format_errors(cfg.error()));
      r["error"]["details"] = std::move(details);
      return dump(r);
    }
    return dump(command_response(id, service.configure(*cfg, who)));
  }
  if (cmd == "start") {
    return dump(command_response(id, service.start(who)));
  }
  if (cmd == "stop") {
    return dump(command_response(id, service.stop(who)));
  }
  if (cmd == "reset") {
    return dump(command_response(id, service.reset(who)));
  }
  return dump(error_response(id, service.state(), "unknown_command", "unknown command \"" + cmd + "\""));
}
// [/snippet:handle]

}  // namespace minidaq::control
