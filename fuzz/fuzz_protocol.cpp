// SPDX-License-Identifier: MIT
// Fuzz target: the control protocol (Chapter 6) as the server sees it: bytes
// from a socket go through the LineFramer, each line through handle_request.
// Every response must be one line of JSON with "api" and a boolean "ok".
// Each input is one connection (Chapter 17): until "auth" succeeds, only hello
// and auth may succeed, and an observer never succeeds with a command that
// changes the acquisition. The seeds hold the two known tokens.
// The service has no adapters, so a fuzzed "start" cannot start threads.
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <string>
#include <string_view>

#include <nlohmann/json.hpp>

#include "minidaq/control/acquisition_service.hpp"
#include "minidaq/control/control_protocol.hpp"

using namespace minidaq::control;

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data, std::size_t size) {
  static AcquisitionService service;  // shared across inputs, like a long-running server
  // Fixed tokens, so that the seeds can authenticate (see fuzz/corpus/protocol/).
  static const TokenStore tokens = TokenStore::single("op", Role::operator_, "mdq_operator");
  static const TokenStore observers = TokenStore::single("obs", Role::observer, "mdq_observer");
  Session session{"fuzz", {}};
  LineFramer framer{4096};
  framer.feed(std::string_view{reinterpret_cast<const char*>(data), size});
  while (auto line = framer.next()) {
    // Odd-length inputs connect to a server whose only token is an observer's.
    const std::string response = handle_request(*line, service, session, size % 2 == 0 ? &tokens : &observers);
    if (response.find('\n') != std::string::npos) {
      std::abort();  // would break the framing of the client
    }
    const auto j = nlohmann::json::parse(response, nullptr, false);
    if (j.is_discarded() || !j.contains("api") || !j.contains("ok") || !j["ok"].is_boolean()) {
      std::abort();
    }
    // [snippet:property]
    const auto req = nlohmann::json::parse(*line, nullptr, false);
    const bool named = req.is_object() && req.contains("cmd") && req["cmd"].is_string();
    const std::string cmd = named ? req["cmd"].get<std::string>() : std::string{};
    if (j["ok"] == true && required_role(cmd) > session.identity.role) {
      std::abort();  // a command succeeded without the role it needs
    }
    if (session.failed_auth) {
      break;  // the server closes the connection here
    }
    // [/snippet:property]
    if (service.state() == AcqState::configured || service.state() == AcqState::fault) {
      (void)service.reset("fuzz");  // keep the state space small between inputs
    }
  }
  return 0;
}
