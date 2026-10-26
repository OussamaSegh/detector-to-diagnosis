// SPDX-License-Identifier: MIT
#include "minidaq/control/control_protocol.hpp"

#include <array>
#include <utility>
#include <vector>

#include <nlohmann/json.hpp>

#include "minidaq/config/acquisition_config.hpp"
#include "minidaq/core/flight_recorder.hpp"
#include "minidaq/rt/crash_report.hpp"

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

CommandId command_id(std::string_view cmd) noexcept {
  constexpr std::array<std::pair<std::string_view, CommandId>, 7> ids{{{"configure", CommandId::configure},
                                                                        {"start", CommandId::start},
                                                                        {"stop", CommandId::stop},
                                                                        {"reset", CommandId::reset},
                                                                        {"status", CommandId::status},
                                                                        {"diagnostics", CommandId::diagnostics},
                                                                        {"auth", CommandId::auth}}};
  for (const auto& [name, cid] : ids) {
    if (name == cmd) {
      return cid;
    }
  }
  return CommandId::other;
}

// Every command but hello reaches the flight recorder with its outcome, refusals included.
std::string traced(std::string_view cmd, const json& response) {
  const auto ok = response.find("ok");
  trace(TraceCode::command, static_cast<std::uint64_t>(command_id(cmd)),
        ok != response.end() && ok->is_boolean() && ok->get<bool>() ? 1U : 0U);
  return dump(response);
}

// [snippet:diagnostics]
json diagnostics(const json& req, const json& id, const AcquisitionService& service) {
  std::size_t n = diagnostics_default_events;
  if (const auto it = req.find("events"); it != req.end()) {
    if (!it->is_number_unsigned() || it->get<std::uint64_t>() > diagnostics_max_events) {
      return error_response(id, service.state(), "bad_request",
                            "\"events\" is a whole number from 0 to " + std::to_string(diagnostics_max_events));
    }
    n = it->get<std::size_t>();
  }
  std::vector<TraceEvent> events(n);
  events.resize(flight_recorder().snapshot_into(events));
  const TraceCounts c = flight_recorder().counts();
  json list = json::array();
  for (const auto& e : events) {
    list.push_back({{"t_ns", e.t_ns}, {"ring", e.ring}, {"seq", e.seq}, {"code", to_string(e.code)},
                    {"a", e.a}, {"b", e.b}});
  }
  return json{{"api", api_version},
              {"id", id},
              {"ok", true},
              {"diagnostics",
               {{"server", std::string{"minidaq "} + MINIDAQ_VERSION_STRING},
                {"build_id", rt::build_id()},
                {"recorder", {{"recorded", c.recorded}, {"dropped", c.dropped}, {"torn", c.torn}}},
                {"events", std::move(list)}}}};
}
// [/snippet:diagnostics]

// [snippet:auth]
json authenticate(const json& req, const json& id, AcquisitionService& service, Session& session,
                  const TokenStore* tokens) {
  if (tokens == nullptr) {  // authentication is off: the identity stays what the server gave
    return json{{"api", api_version}, {"id", id}, {"ok", true}, {"identity", session.identity.name},
                {"role", to_string(session.identity.role)}};
  }
  // Not req.value("token", ...): it throws when "token" is there but not a string (MDQ-PR-013).
  const auto it = req.find("token");
  const std::string token = it != req.end() && it->is_string() ? it->get<std::string>() : std::string{};
  const auto who = tokens->check(token);
  if (!who) {
    // The token is never recorded: a mistyped token is often one character from a real one.
    session.failed_auth = true;
    service.note(session.peer, "auth", "refused: unknown token", false);
    return error_response(id, service.state(), "unauthenticated", "unknown token; the connection is closed");
  }
  session.identity = *who;
  service.note(session.who(), "auth", std::string{to_string(who->role)});
  return json{{"api", api_version}, {"id", id}, {"ok", true}, {"identity", who->name}, {"role", to_string(who->role)}};
}
// [/snippet:auth]

}  // namespace

std::string Session::who() const { return identity.name.empty() ? peer : identity.name + "@" + peer; }

// [snippet:handle]
std::string handle_request(std::string_view line, AcquisitionService& service, Session& session,
                           const TokenStore* tokens) {
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
                     {"auth", tokens != nullptr ? "token" : "none"},
                     {"commands", {"hello", "auth", "configure", "start", "stop", "reset", "status", "diagnostics"}}});
  }
  if (cmd == "auth") {
    return traced(cmd, authenticate(req, id, service, session, tokens));
  }
  // [snippet:authorize]
  const Role needed = required_role(cmd);
  if (needed > session.identity.role) {
    const bool anonymous = session.identity.role == Role::none;
    service.note(session.who(), cmd, anonymous ? "refused: not authenticated" : "refused: role", false);
    return traced(cmd, error_response(id, service.state(), anonymous ? "unauthenticated" : "forbidden",
                               anonymous ? "authenticate first (\"auth\")"
                                         : "\"" + cmd + "\" needs the role " + std::string{to_string(needed)}));
  }
  // [/snippet:authorize]
  const std::string who = session.who();
  if (cmd == "status") {
    return traced(cmd, json{{"api", api_version}, {"id", id}, {"ok", true}, {"status", service.status()}});
  }
  if (cmd == "diagnostics") {
    return traced(cmd, diagnostics(req, id, service));
  }
  if (cmd == "configure") {
    if (!req.contains("config")) {
      return traced(cmd, error_response(id, service.state(), "bad_request", "configure needs \"config\""));
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
      return traced(cmd, r);
    }
    return traced(cmd, command_response(id, service.configure(*cfg, who)));
  }
  if (cmd == "start") {
    return traced(cmd, command_response(id, service.start(who)));
  }
  if (cmd == "stop") {
    return traced(cmd, command_response(id, service.stop(who)));
  }
  if (cmd == "reset") {
    return traced(cmd, command_response(id, service.reset(who)));
  }
  return traced(cmd, error_response(id, service.state(), "unknown_command", "unknown command \"" + cmd + "\""));
}
// [/snippet:handle]

}  // namespace minidaq::control
