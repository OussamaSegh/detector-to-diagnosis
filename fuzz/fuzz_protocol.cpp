// SPDX-License-Identifier: MIT
// Fuzz target: the control protocol (Chapter 6) as the server sees it: bytes
// from a socket go through the LineFramer, each line through handle_request.
// Every response must be one line of JSON with "api" and a boolean "ok".
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
  LineFramer framer{4096};
  framer.feed(std::string_view{reinterpret_cast<const char*>(data), size});
  while (auto line = framer.next()) {
    const std::string response = handle_request(*line, service, "fuzz");
    if (response.find('\n') != std::string::npos) {
      std::abort();  // would break the framing of the client
    }
    const auto j = nlohmann::json::parse(response, nullptr, false);
    if (j.is_discarded() || !j.contains("api") || !j.contains("ok") || !j["ok"].is_boolean()) {
      std::abort();
    }
    if (service.state() == AcqState::configured || service.state() == AcqState::fault) {
      (void)service.reset("fuzz");  // keep the state space small between inputs
    }
  }
  return 0;
}
