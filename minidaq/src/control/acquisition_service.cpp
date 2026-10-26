// SPDX-License-Identifier: MIT
#include "minidaq/control/acquisition_service.hpp"

#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

#include <cerrno>

#include <nlohmann/json.hpp>

#include "minidaq/control/run_integrity.hpp"
#include "minidaq/core/flight_recorder.hpp"

namespace minidaq::control {

namespace {

using nlohmann::json;

json latency_json(const LatencyHistogram& h) {
  const LatencySummary s = h.summary();
  return json{{"count", s.count}, {"p50", s.p50}, {"p99", s.p99}, {"p999", s.p999}, {"max", s.max}};
}

json interval_json(const LatencyHistogram& h, const HistogramCounts& before, const HistogramCounts& after) {
  const LatencySummary s = interval_summary(h, before, after);
  return json{{"count", s.count}, {"p50", s.p50}, {"p99", s.p99}, {"p999", s.p999}, {"max", s.max}};
}

json hardware_json(const HardwarePort& hw) {
  json boards = json::array();
  for (const HardwareBoard& b : hw.boards()) {
    boards.push_back({{"slot", b.slot},
                      {"state", b.state},
                      {"temperature_c", b.temperature_c},
                      {"temperature", b.temp_level},
                      {"target_v", b.target_v},
                      {"setpoint_v", b.setpoint_v},
                      {"monitor_v", b.monitor_v},
                      {"current_ua", b.current_ua},
                      {"at_limit", b.at_limit},
                      {"fault", b.fault.empty() ? json(nullptr) : json(b.fault)}});
  }
  const auto not_ready = hw.not_ready();
  return json{{"describe", hw.describe()},
              {"ready", !not_ready.has_value()},
              {"not_ready", not_ready ? json(*not_ready) : json(nullptr)},
              {"boards", std::move(boards)}};
}

// [snippet:read_small_file]
// The path comes from a control client, so it is untrusted input (Chapter 7):
// only regular files, and only small ones. Without these checks "/dev/zero"
// would make the control thread read forever, and a FIFO would block it.
// Open first, then check the open descriptor: checking the path and opening
// it afterwards would leave a window in which the file can be swapped.
constexpr std::size_t max_profile_bytes = std::size_t{64} * 1024;

std::string read_small_file(const std::string& path, std::string& out) {
  const int fd = ::open(path.c_str(), O_RDONLY | O_CLOEXEC | O_NONBLOCK);  // a FIFO must not block
  if (fd < 0) {
    return "cannot read \"" + path + "\"";
  }
  struct stat st {};
  std::string problem;
  if (::fstat(fd, &st) != 0 || !S_ISREG(st.st_mode)) {
    problem = "\"" + path + "\" is not a regular file";
  } else if (static_cast<std::size_t>(st.st_size) > max_profile_bytes) {
    problem = "\"" + path + "\" is larger than 64 KiB";
  } else {
    std::string buf(max_profile_bytes + 1, '\0');  // +1: notice a file that grew
    std::size_t n = 0;
    for (;;) {
      const ssize_t r = ::read(fd, buf.data() + n, buf.size() - n);
      if (r > 0) {
        n += static_cast<std::size_t>(r);
        if (n == buf.size()) {
          break;
        }
      } else if (r == 0 || errno != EINTR) {
        break;
      }
    }
    if (n > max_profile_bytes) {
      problem = "\"" + path + "\" is larger than 64 KiB";
    } else {
      out.assign(buf.data(), n);
    }
  }
  ::close(fd);
  return problem;
}
// [/snippet:read_small_file]

}  // namespace

AcquisitionService::AcquisitionService(ServiceOptions options)
    : opt_{std::move(options)},
      machine_{[this](const Transition& t) {
        trace(TraceCode::state, static_cast<std::uint64_t>(t.from), static_cast<std::uint64_t>(t.to));
        note("service", "transition",
             std::string{to_string(t.from)} + " -> " + std::string{to_string(t.to)} + " (" +
                 std::string{to_string(t.event)} + ")");
        {
          const std::lock_guard lock{wait_mu_};  // pairs with wait_for()
          observed_.store(t.to);
        }
        wait_cv_.notify_all();
      }} {
  monitor_ = std::jthread{[this](const std::stop_token& st) { monitor(st); }};
}

AcquisitionService::~AcquisitionService() {
  monitor_.request_stop();
  if (monitor_.joinable()) {
    monitor_.join();
  }
  const std::lock_guard lock{mu_};
  if (pipeline_) {
    pipeline_->request_stop();
    pipeline_->wait();
  }
}

void AcquisitionService::note(std::string_view who, std::string_view action, std::string_view detail,
                              bool ok) const {
  if (opt_.audit) {
    opt_.audit(AuditRecord{utc_now_iso8601(), std::string{who}, std::string{action}, std::string{detail}, ok});
  }
}

CommandResult AcquisitionService::result(bool ok, std::string code, std::string message) const {
  return CommandResult{ok, machine_.state(), std::move(code), std::move(message)};
}

CommandResult AcquisitionService::illegal(AcqEvent e) const {
  return result(false, "illegal_transition", IllegalTransition{machine_.state(), e}.message());
}

// [snippet:configure]
CommandResult AcquisitionService::configure(const config::AcquisitionConfig& cfg, std::string_view who) {
  const std::lock_guard lock{mu_};
  if (!next_state(machine_.state(), AcqEvent::configure)) {
    note(who, "configure", "rejected: " + IllegalTransition{machine_.state(), AcqEvent::configure}.message(), false);
    return illegal(AcqEvent::configure);
  }
  std::optional<rt::RtProfile> profile;
  if (!cfg.rt_profile.empty()) {
    std::string text;
    if (const std::string problem = read_small_file(cfg.rt_profile, text); !problem.empty()) {
      note(who, "configure", "rejected: " + problem, false);
      return result(false, "config_error", "/rt_profile: " + problem);
    }
    auto parsed = rt::parse_profile(text);
    if (!parsed) {
      note(who, "configure", "rejected: bad profile " + cfg.rt_profile, false);
      return result(false, "config_error", "/rt_profile: " + parsed.error().message);
    }
    profile = *parsed;
  }
  config_ = cfg;
  profile_ = profile;
  note(who, "configure", config::to_json(cfg).dump());
  (void)machine_.apply(AcqEvent::configure);
  return result(true);
}
// [/snippet:configure]

CommandResult AcquisitionService::start(std::string_view who) {
  const std::lock_guard lock{mu_};
  // configured implies a configuration; test both rather than rely on the invariant.
  if (machine_.state() != AcqState::configured || !config_) {
    note(who, "start", "rejected: " + IllegalTransition{machine_.state(), AcqEvent::start}.message(), false);
    return illegal(AcqEvent::start);
  }
  if (auto why = opt_.hardware ? opt_.hardware->not_ready() : std::nullopt) {
    note(who, "start", "hardware not ready: " + *why, false);
    return result(false, "device_error", "hardware not ready: " + *why);
  }
  const config::AcquisitionConfig& cfg = *config_;
  // Fresh ports for every run: a detector's clock and counters start at zero.
  // The previous run's adapters are released first, because a device that
  // owns an exclusive resource cannot be opened twice: the UDP detector of
  // Chapter 9 holds its port. The previous run's counters go with them, also
  // when this start then fails.
  pipeline_.reset();  // first: it calls into the detector and the sink
  detector_.reset();
  sink_.reset();
  std::string error;
  if (!opt_.detector || !opt_.sink) {
    note(who, "start", "no detector or sink adapter", false);
    return result(false, "device_error", "no detector or sink adapter configured");
  }
  auto detector = opt_.detector(cfg, error);
  if (!detector) {
    note(who, "start", "device error: " + error, false);
    return result(false, "device_error", error);
  }
  auto sink = opt_.sink(cfg, error);
  if (!sink) {
    note(who, "start", "sink error: " + error, false);
    return result(false, "device_error", error);
  }
  detector_ = std::move(detector);
  sink_ = std::move(sink);
  PipelineConfig pc = config::to_pipeline_config(cfg);
  if (profile_) {
    pc.rt = *profile_;
  }
  pc.due_time_ns = detector_->due_times();
  DetectorPort* d = detector_.get();
  CoincidenceSinkPort* s = sink_.get();
  pipeline_ = std::make_unique<AcquisitionPipeline>(
      pc, [d](std::span<std::uint64_t> out) { return d->read(out); },
      [s](std::span<const Coincidence> c) { s->write(c); });
  ++run_id_;
  fault_.clear();
  run_started_utc_ = utc_now_iso8601();
  run_started_ = std::chrono::steady_clock::now();
  run_ended_set_ = false;
  snapshot_previous_.reset();
  snapshot_latest_.reset();
  pipeline_->start();
  take_latency_snapshot_locked();
  trace(TraceCode::run_begin, run_id_);
  note(who, "start", "run " + std::to_string(run_id_) + ", " + detector_->describe());
  (void)machine_.apply(AcqEvent::start);
  return result(true);
}

CommandResult AcquisitionService::stop(std::string_view who) {
  const std::lock_guard lock{mu_};
  if (machine_.state() != AcqState::running) {
    note(who, "stop", "rejected: " + IllegalTransition{machine_.state(), AcqEvent::stop}.message(), false);
    return illegal(AcqEvent::stop);
  }
  pipeline_->request_stop();  // the stages drain; the monitor sees them finish
  note(who, "stop", "run " + std::to_string(run_id_));
  (void)machine_.apply(AcqEvent::stop);
  return result(true);
}

CommandResult AcquisitionService::reset(std::string_view who) {
  const std::lock_guard lock{mu_};
  if (!next_state(machine_.state(), AcqEvent::reset)) {
    note(who, "reset", "rejected: " + IllegalTransition{machine_.state(), AcqEvent::reset}.message(), false);
    return illegal(AcqEvent::reset);
  }
  if (pipeline_) {
    // After a fault the stages may still be draining; wait for them here,
    // so that idle really means "nothing is running".
    pipeline_->request_stop();
    pipeline_->wait();
  }
  if (opt_.hardware && machine_.state() == AcqState::fault) {
    opt_.hardware->acknowledge();  // the operator has seen the fault (SRS-HW-005)
  }
  pipeline_.reset();
  detector_.reset();
  sink_.reset();
  config_.reset();
  profile_.reset();
  snapshot_previous_.reset();
  snapshot_latest_.reset();
  fault_.clear();
  note(who, "reset", "");
  (void)machine_.apply(AcqEvent::reset);
  return result(true);
}

void AcquisitionService::enter_fault_locked(std::string reason, std::string_view who) {
  const AcqState s = machine_.state();
  if (pipeline_ && (s == AcqState::running || s == AcqState::stopping)) {
    pipeline_->request_stop();  // stop taking data; reset() waits for the drain
    run_ended_ = std::chrono::steady_clock::now();
    run_ended_set_ = true;
  }
  fault_ = std::move(reason);
  const auto source = fault_.starts_with("detector:") ? FaultSource::detector
                      : fault_.starts_with("sink:")   ? FaultSource::sink
                      : fault_.starts_with("sort:")   ? FaultSource::sorter
                      : fault_.starts_with("hw:")     ? FaultSource::hardware
                                                      : FaultSource::other;
  trace(TraceCode::fault, run_id_, static_cast<std::uint64_t>(source));
  note(who, "fault", fault_, false);
  (void)machine_.apply(AcqEvent::error);
}

void AcquisitionService::take_latency_snapshot_locked() {
  LatencySnapshot snap;
  snap.taken = std::chrono::steady_clock::now();
  for (std::size_t i = 0; i < num_stages; ++i) {
    snap.histograms[i] = snapshot_counts(pipeline_->stage_latency(static_cast<StageId>(i)));
  }
  snap.histograms[num_stages] = snapshot_counts(pipeline_->end_to_end_latency());
  snapshot_previous_ = std::move(snapshot_latest_);
  snapshot_latest_ = std::move(snap);
}

// [snippet:monitor]
void AcquisitionService::check_run_locked() {
  const AcqState s = machine_.state();
  // The boards are watched in every state: a fault while idle is reported at once, not when
  // the next run starts.
  if (auto f = opt_.hardware && s != AcqState::fault ? opt_.hardware->fault() : std::nullopt) {
    return enter_fault_locked("hw: " + *f, "service");
  }
  if (s != AcqState::running && s != AcqState::stopping) {
    return;
  }
  if (auto f = detector_ ? detector_->fault() : std::nullopt) {
    return enter_fault_locked("detector: " + *f, "service");
  }
  if (auto f = sink_ ? sink_->fault() : std::nullopt) {
    return enter_fault_locked("sink: " + *f, "service");
  }
  if (pipeline_ && pipeline_->late_singles() > 0) {
    // The sorter cannot put these back in order, so coincidences may be
    // missing or wrong: stop instead of producing them silently (Chapter 1).
    return enter_fault_locked("sort: " + std::to_string(pipeline_->late_singles()) +
                                  " singles arrived out of time order",
                              "service");
  }
  if (snapshot_latest_ && std::chrono::steady_clock::now() - snapshot_latest_->taken >= opt_.interval_period) {
    take_latency_snapshot_locked();
  }
  if (pipeline_ && pipeline_->finished()) {
    pipeline_->wait();  // all stages are done: this only joins the threads
    // The last write() has returned: the sink can make the run durable, with
    // the run's record (counters included) next to the data. A run whose data
    // did not reach stable storage ends in a fault.
    const json record = status_locked();
    if (auto e = sink_ ? sink_->close(record.dump()) : std::nullopt) {
      return enter_fault_locked("sink: " + *e, "service");
    }
    run_ended_ = std::chrono::steady_clock::now();
    run_ended_set_ = true;
    note("service", "run_ended", "run " + std::to_string(run_id_));
    trace(TraceCode::run_end, run_id_, record["integrity"]["complete"].get<bool>() ? 1U : 0U);
    // [snippet:incomplete]
    if (!record["integrity"]["complete"].get<bool>()) {
      std::string losses;
      for (const auto& l : record["integrity"]["losses"]) {
        losses += (losses.empty() ? "" : ", ") + l["counter"].get<std::string>() + " = " + l["count"].dump();
      }
      note("service", "data_incomplete", "run " + std::to_string(run_id_) + ": " + losses, false);
    }
    // [/snippet:incomplete]
    (void)machine_.apply(AcqEvent::drained);
  }
}

void AcquisitionService::monitor(const std::stop_token& st) {
  while (!st.stop_requested()) {
    {
      const std::lock_guard lock{mu_};
      check_run_locked();
    }
    std::unique_lock lock{wait_mu_};
    wait_cv_.wait_for(lock, st, opt_.monitor_period, [] { return false; });
  }
}
// [/snippet:monitor]

bool AcquisitionService::wait_for(AcqState s, std::chrono::milliseconds timeout) const {
  std::unique_lock lock{wait_mu_};
  return wait_cv_.wait_for(lock, timeout, [&] { return observed_.load() == s; });
}

json AcquisitionService::status() const {
  const std::lock_guard lock{mu_};
  return status_locked();
}

json AcquisitionService::status_locked() const {
  json j;
  j["state"] = std::string{to_string(machine_.state())};
  j["run_id"] = run_id_;
  j["fault"] = fault_.empty() ? json(nullptr) : json(fault_);
  j["config"] = config_ ? config::to_json(*config_) : json(nullptr);
  j["detector"] = detector_ ? json(detector_->describe()) : json(nullptr);
  if (detector_) {
    json counters = json::object();
    for (const auto& c : detector_->counters()) {
      counters[c.name] = c.value;
    }
    j["detector_counters"] = std::move(counters);
  }
  j["sink"] = sink_ ? json(sink_->describe()) : json(nullptr);
  if (sink_) {
    json counters = json::object();
    for (const auto& c : sink_->counters()) {
      counters[c.name] = c.value;
    }
    j["sink_counters"] = std::move(counters);
  }
  if (pipeline_) {
    const auto end = run_ended_set_ ? run_ended_ : std::chrono::steady_clock::now();
    j["run"] = {{"started_utc", run_started_utc_},
                {"elapsed_s", std::chrono::duration<double>(end - run_started_).count()}};
    json stages = json::array();
    for (const StageSnapshot& st : pipeline_->stats()) {
      stages.push_back({{"name", st.name},
                        {"in", st.items_in},
                        {"out", st.items_out},
                        {"dropped", st.items_dropped},
                        {"filtered", st.items_filtered},
                        {"batches", st.batches}});
    }
    j["stages"] = std::move(stages);
    json lat;
    for (std::size_t i = 0; i < num_stages; ++i) {
      lat[std::string{pipeline_->stats()[i].name}] = latency_json(pipeline_->stage_latency(static_cast<StageId>(i)));
    }
    lat["end_to_end"] = latency_json(pipeline_->end_to_end_latency());
    j["latency_ns"] = std::move(lat);
    j["late_singles"] = pipeline_->late_singles();
    const SorterStats so = pipeline_->sorter_stats();
    j["sorter"] = {{"singles_in", so.singles_in},
                   {"energy_rejected", so.energy_rejected},
                   {"out_of_order", so.out_of_order},
                   {"singles_alone", so.singles_alone},
                   {"pair_windows", so.pair_windows},
                   {"multiple_windows", so.multiple_windows},
                   {"singles_in_multiples", so.singles_in_multiples},
                   {"geometry_rejected", so.geometry_rejected},
                   {"prompts", so.prompts},
                   {"prompts_from_multiples", so.prompts_from_multiples},
                   {"delayed", so.delayed}};
    if (snapshot_previous_ && snapshot_latest_) {
      // The last completed interval: between the two most recent snapshots.
      json recent;
      recent["interval_s"] = std::chrono::duration<double>(snapshot_latest_->taken - snapshot_previous_->taken).count();
      for (std::size_t i = 0; i <= num_stages; ++i) {
        const LatencyHistogram& h = i < num_stages ? pipeline_->stage_latency(static_cast<StageId>(i))
                                                   : pipeline_->end_to_end_latency();
        const std::string name = i < num_stages ? std::string{pipeline_->stats()[i].name} : "end_to_end";
        recent[name] = interval_json(h, snapshot_previous_->histograms[i], snapshot_latest_->histograms[i]);
      }
      j["recent_latency_ns"] = std::move(recent);
    }
  }
  j["hardware"] = opt_.hardware ? hardware_json(*opt_.hardware) : json(nullptr);  // 2.2: Chapter 22
  j["integrity"] = assess_integrity(j);  // risk control RC-01
  return j;
}

}  // namespace minidaq::control
