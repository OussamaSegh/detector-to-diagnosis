// SPDX-License-Identifier: MIT
// MiniDAQ - the acquisition service: the application core (Chapter 6).
//
// Owns the state machine, the configuration, the ports and the pipeline of the
// current run. Every control client (the TCP API, a test, a future GUI) goes
// through these five commands and status(); none of them touches the pipeline
// directly. The acquisition belongs to the service, not to a client session:
// a client that disconnects does not stop a run (docs/adr/0003).
//
// A monitor thread, never the hot path, turns system events into state
// changes: a run that ended by itself or finished draining ("drained"), and a
// fault reported by a port or by the pipeline ("error"), and once per
// interval_period a snapshot of the latency histograms.
#pragma once

#include <array>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>
#include <thread>

#include <nlohmann/json_fwd.hpp>

#include "minidaq/config/acquisition_config.hpp"
#include "minidaq/control/acquisition_state.hpp"
#include "minidaq/control/audit.hpp"
#include "minidaq/control/ports.hpp"
#include "minidaq/metrics/histogram_interval.hpp"
#include "minidaq/pipeline/acquisition_pipeline.hpp"

namespace minidaq::control {

struct ServiceOptions {
  // The service knows only the ports. Which adapters fill them is decided by
  // whoever builds the service: the application (with_default_adapters()),
  // or a test with its own doubles. Without a detector or a sink, start()
  // fails with device_error.
  DetectorFactory detector;
  SinkFactory sink;
  AuditSink audit;  // empty: no audit trail
  std::chrono::milliseconds monitor_period{20};
  // status() reports latency percentiles over the last completed interval of
  // this length, as well as since the start of the run.
  std::chrono::milliseconds interval_period{1000};
};

struct CommandResult {
  bool ok = false;
  AcqState state = AcqState::idle;  // the state after the command
  std::string code;                 // "" on success; "illegal_transition", "config_error", "device_error"
  std::string message;
};

class AcquisitionService {
 public:
  explicit AcquisitionService(ServiceOptions options = {});
  ~AcquisitionService();  // stops a running acquisition and drains it
  AcquisitionService(const AcquisitionService&) = delete;
  AcquisitionService& operator=(const AcquisitionService&) = delete;
  AcquisitionService(AcquisitionService&&) = delete;
  AcquisitionService& operator=(AcquisitionService&&) = delete;

  // [snippet:commands]
  CommandResult configure(const config::AcquisitionConfig& cfg, std::string_view who);
  CommandResult start(std::string_view who);
  CommandResult stop(std::string_view who);
  CommandResult reset(std::string_view who);
  // [/snippet:commands]

  [[nodiscard]] AcqState state() const { return machine_.state(); }
  // A snapshot for the control API: state, run, configuration, per-stage
  // counters and latency percentiles. Safe to call at any time.
  [[nodiscard]] nlohmann::json status() const;
  // Blocks until the state is `s` or the timeout expires; returns whether it got there.
  bool wait_for(AcqState s, std::chrono::milliseconds timeout) const;
  // Records an event in the audit trail without changing anything.
  void note(std::string_view who, std::string_view action, std::string_view detail, bool ok = true) const;

 private:
  void monitor(const std::stop_token& st);
  void check_run_locked();
  [[nodiscard]] nlohmann::json status_locked() const;
  void enter_fault_locked(std::string reason, std::string_view who);
  void take_latency_snapshot_locked();
  CommandResult result(bool ok, std::string code = {}, std::string message = {}) const;
  CommandResult illegal(AcqEvent e) const;

  ServiceOptions opt_;
  StateMachine machine_;
  mutable std::mutex mu_;  // everything below; taken before the state machine's own lock
  std::optional<config::AcquisitionConfig> config_;
  std::optional<rt::RtProfile> profile_;
  std::unique_ptr<DetectorPort> detector_;
  std::unique_ptr<CoincidenceSinkPort> sink_;
  std::unique_ptr<AcquisitionPipeline> pipeline_;
  std::uint64_t run_id_ = 0;
  std::string run_started_utc_;
  std::chrono::steady_clock::time_point run_started_{};
  std::chrono::steady_clock::time_point run_ended_{};
  bool run_ended_set_ = false;
  std::string fault_;
  // Latency histogram counts (one per stage, then end to end) at the start of
  // the last two intervals, for "recent" percentiles. Monitor thread writes.
  struct LatencySnapshot {
    std::chrono::steady_clock::time_point taken{};
    std::array<HistogramCounts, num_stages + 1> histograms;
  };
  std::optional<LatencySnapshot> snapshot_previous_;
  std::optional<LatencySnapshot> snapshot_latest_;
  // Waiting for a state: the transition listener publishes each new state
  // here, so waiters never take the state machine's lock.
  std::atomic<AcqState> observed_{AcqState::idle};
  mutable std::mutex wait_mu_;
  mutable std::condition_variable_any wait_cv_;
  std::jthread monitor_;  // last: started after everything else exists
};

}  // namespace minidaq::control
