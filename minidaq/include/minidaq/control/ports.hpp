// SPDX-License-Identifier: MIT
// MiniDAQ - ports: the interfaces through which the acquisition core reaches
// the outside world (Chapter 6).
//
// The core (state machine, pipeline, service) depends on these interfaces,
// never on a concrete device, socket or file. Adapters implement them: a
// simulated detector today, the UDP receiver of Chapter 9 later, and test
// doubles that inject faults. This is dependency inversion: the policy (how
// an acquisition runs) does not depend on the details (where the words come
// from), so every hardware dependency can be simulated in a test.
#pragma once

#include <cstdint>
#include <functional>
#include <memory>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

#include "minidaq/config/acquisition_config.hpp"
#include "minidaq/core/single.hpp"

namespace minidaq::control {

struct DetectorCounter {
  std::string name;
  std::uint64_t value = 0;
};

// [snippet:ports]
// Where packed words come from. read() runs on the pipeline's source thread
// and must not block for long: return 0 when nothing is available.
class DetectorPort {
 public:
  virtual ~DetectorPort() = default;
  // Fills up to out.size() words; returns how many (0: nothing right now).
  virtual std::size_t read(std::span<std::uint64_t> out) = 0;
  // When word `index` was due, if the device knows (Chapter 4); else empty.
  [[nodiscard]] virtual std::function<std::int64_t(std::uint64_t)> due_times() { return {}; }
  // A fault the device has detected (link down, overflow, ...). Polled by the
  // service from its monitor thread, never from the hot path. Thread-safe.
  [[nodiscard]] virtual std::optional<std::string> fault() const { return std::nullopt; }
  [[nodiscard]] virtual std::string describe() const = 0;
  // Device-specific counters for the status report (Chapter 9: packets lost,
  // reordered, ...). Thread-safe, like fault().
  [[nodiscard]] virtual std::vector<DetectorCounter> counters() const { return {}; }
};

// Where coincidences go. write() runs on the pipeline's writer thread.
class CoincidenceSinkPort {
 public:
  virtual ~CoincidenceSinkPort() = default;
  virtual void write(std::span<const Coincidence> batch) = 0;
  // Ends the run (Chapter 12): called once by the service after the last
  // write(), when the pipeline has drained. run_record is the run's record as
  // JSON text: the service's final status, with the configuration and the
  // counters of the link and of every stage. A sink that stores data makes it
  // durable here, keeps the record next to it, and returns an error if it
  // could not do both.
  [[nodiscard]] virtual std::optional<std::string> close(std::string_view /*run_record*/) { return std::nullopt; }
  [[nodiscard]] virtual std::optional<std::string> fault() const { return std::nullopt; }
  [[nodiscard]] virtual std::string describe() const = 0;
  // Sink-specific counters for the status report, like DetectorPort's. Thread-safe.
  [[nodiscard]] virtual std::vector<DetectorCounter> counters() const { return {}; }
};

// The service creates a fresh detector and sink for every configuration.
using DetectorFactory =
    std::function<std::unique_ptr<DetectorPort>(const config::AcquisitionConfig&, std::string& error)>;
using SinkFactory =
    std::function<std::unique_ptr<CoincidenceSinkPort>(const config::AcquisitionConfig&, std::string& error)>;
// [/snippet:ports]

}  // namespace minidaq::control
