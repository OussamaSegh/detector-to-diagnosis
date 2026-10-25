// SPDX-License-Identifier: MIT
#include "minidaq/control/adapters.hpp"

#include <cstdio>

#include "minidaq/control/listmode_sink.hpp"
#include "minidaq/control/udp_detector.hpp"

namespace minidaq::control {

namespace {
sim::SyntheticConfig synthetic(const config::SourceSettings& s) {
  sim::SyntheticConfig c;
  c.rate_hz = s.rate_hz;
  c.pair_fraction = s.pair_fraction;
  c.seed = s.seed;
  return c;
}
}  // namespace

SimulatedDetector::SimulatedDetector(const config::SourceSettings& s) : source_{synthetic(s), s.rate_hz} {
  char buf[96];
  // snprintf truncates rather than overflows; a negative result is an encoding error.
  const int n = std::snprintf(buf, sizeof buf, "simulated detector, %.3g singles/s, seed %llu", s.rate_hz,
                              static_cast<unsigned long long>(s.seed));
  description_ = n >= 0 ? buf : "simulated detector";
}

std::unique_ptr<DetectorPort> make_default_detector(const config::AcquisitionConfig& c, std::string& error) {
  if (c.source.type == "synthetic") {
    return std::make_unique<SimulatedDetector>(c.source);
  }
  if (c.source.type == "udp") {
    auto d = UdpDetector::open(c.source.udp);
    if (!d) {
      error = d.error();
      return nullptr;
    }
    return std::move(*d);
  }
  error = "no adapter for source type \"" + c.source.type + "\"";
  return nullptr;
}

std::unique_ptr<CoincidenceSinkPort> make_default_sink(const config::AcquisitionConfig& c, std::string& error) {
  if (c.output.type == "listmode") {
    return make_listmode_sink(c, error);
  }
  return std::make_unique<CountingSink>();
}

ServiceOptions with_default_adapters(ServiceOptions o) {
  if (!o.detector) {
    o.detector = make_default_detector;
  }
  if (!o.sink) {
    o.sink = make_default_sink;
  }
  return o;
}

}  // namespace minidaq::control
