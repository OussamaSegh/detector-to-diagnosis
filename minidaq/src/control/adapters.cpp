// SPDX-License-Identifier: MIT
#include "minidaq/control/adapters.hpp"

#include <cstdio>
#include <string>
#include <vector>

#include "minidaq/control/listmode_sink.hpp"
#include "minidaq/control/udp_detector.hpp"
#if MINIDAQ_WITH_SIMULATOR
#include "minidaq/sim/paced_source.hpp"
#endif

namespace minidaq::control {

#if MINIDAQ_WITH_SIMULATOR
namespace {
// Synthetic singles delivered at the configured rate, with due times.
class SimulatedDetector final : public DetectorPort {
 public:
  explicit SimulatedDetector(const config::SourceSettings& s);
  std::size_t read(std::span<std::uint64_t> out) override { return source_(out); }
  [[nodiscard]] std::function<std::int64_t(std::uint64_t)> due_times() override {
    return [this](std::uint64_t i) { return source_.due_ns(i); };
  }
  [[nodiscard]] std::string describe() const override { return description_; }

 private:
  sim::PacedSource source_;
  std::string description_;
};

sim::SyntheticConfig synthetic(const config::SourceSettings& s) {
  sim::SyntheticConfig c;
  c.rate_hz = s.rate_hz;
  c.pair_fraction = s.pair_fraction;
  c.seed = s.seed;
  return c;
}

// The readout nodes of schema 2.2 (CR-0037); one node bypasses the merge.
sim::NodeLayout layout(const config::NodeSettings& n) {
  std::vector<Picoseconds> offsets;
  offsets.reserve(n.clock_offsets_ps.size());
  for (const std::int64_t o : n.clock_offsets_ps) {
    offsets.emplace_back(o);
  }
  return sim::NodeLayout::contiguous(n.count, std::move(offsets));
}

SimulatedDetector::SimulatedDetector(const config::SourceSettings& s)
    : source_{synthetic(s), s.rate_hz, layout(s.nodes)} {
  char buf[96];
  // snprintf truncates rather than overflows; a negative result is an encoding error.
  const int n = std::snprintf(buf, sizeof buf, "simulated detector, %.3g singles/s, seed %llu", s.rate_hz,
                              static_cast<unsigned long long>(s.seed));
  description_ = n >= 0 ? buf : "simulated detector";
  if (s.nodes.count > 1) {
    description_ += ", " + std::to_string(s.nodes.count) + " readout nodes merged";
  }
}
}  // namespace
#endif

std::unique_ptr<DetectorPort> make_default_detector(const config::AcquisitionConfig& c, std::string& error) {
  if (c.source.type == "synthetic") {
#if MINIDAQ_WITH_SIMULATOR
    return std::make_unique<SimulatedDetector>(c.source);
#else
    error = std::string{"source type \"synthetic\": "} + no_simulator_in_product;
    return nullptr;
#endif
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

ServiceOptions with_default_adapters(ServiceOptions o,
                                     std::shared_ptr<const signing::SigningKey> run_key) {
  if (!o.detector) {
    o.detector = make_default_detector;
  }
  if (!o.sink && run_key) {
    o.sink = [run_key](const config::AcquisitionConfig& c,
                       std::string& error) -> std::unique_ptr<CoincidenceSinkPort> {
      if (c.output.type == "listmode") {
        return make_listmode_sink(c, error, run_key);
      }
      return make_default_sink(c, error);
    };
  }
  if (!o.sink) {
    o.sink = make_default_sink;
  }
  return o;
}

}  // namespace minidaq::control
