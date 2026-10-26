// SPDX-License-Identifier: MIT
// MiniDAQ - two installation slots and the switch between them (Chapter 25, ADR 0020).
//
// The programs live in one of two directories, ROOT/slots/a and ROOT/slots/b, and run from
// ROOT/current, a symbolic link to one of them. An update is written into the slot that is not
// running, verified there, recorded in ROOT/state.json as a trial, and only then made current, by
// renaming a new link over the old one: rename(2) replaces it atomically, so at every instant
// `current` names a complete, verified version. The service then restarts. A trial that comes up
// (READY) is confirmed and becomes the good version; one that fails to start is rolled back by
// switching the link back to the good slot, which nothing has touched.
//
// Every step is ordered so that a power cut between any two of them leaves a state that open()
// can repair without a person: an install cut before the switch is discarded, a rollback cut
// after the switch is completed. Tests stop each operation after each step (StepHook) and check
// that the store opens again with `current` naming a verified version.
//
// One process at a time: open() takes an exclusive lock on ROOT/lock for the store's lifetime.
#pragma once

#include <cstdint>
#include <filesystem>
#include <functional>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "minidaq/core/expected.hpp"
#include "minidaq/update/bundle.hpp"

namespace minidaq::update {

// [snippet:state]
struct SlotState {
  std::string good;  // "a" or "b": the slot of the last confirmed version
  std::string good_version;
  std::optional<std::string> trial;  // the slot of an installed version not yet confirmed
  std::string trial_version;
};
// [/snippet:state]

struct InstallOptions {
  std::filesystem::path keys_dir;  // the trusted public keys
  std::string platform;            // this PC's platform definition; the bundle must name it
  bool allow_older = false;        // a version not newer than the good one (a deliberate downgrade)
};

enum class Outcome : std::uint8_t { done, nothing_to_do };

// Checks that every regular file under `slot` is listed in its MANIFEST.sha256 with its digest,
// that every listed file exists, and that there is nothing else (no links, no devices).
[[nodiscard]] Expected<std::size_t, std::string> verify_tree(const std::filesystem::path& slot);

class SlotStore {
 public:
  // Called after each step of an operation with the step's name; a test throws from it to stop
  // the operation there, as a power cut would.
  using StepHook = std::function<void(std::string_view step)>;

  // Takes the lock, reads the state and repairs what an interrupted operation left.
  [[nodiscard]] static Expected<SlotStore, std::string> open(std::filesystem::path root,
                                                             StepHook hook = {});
  ~SlotStore();
  SlotStore(SlotStore&& other) noexcept;
  SlotStore& operator=(SlotStore&& other) noexcept;
  SlotStore(const SlotStore&) = delete;
  SlotStore& operator=(const SlotStore&) = delete;

  // Verifies the bundle in `bundle_dir` and installs it as a trial in the slot not running (the
  // first installation is confirmed at once: there is nothing to go back to). Returns a summary.
  [[nodiscard]] Expected<std::string, std::string> install(const std::filesystem::path& bundle_dir,
                                                           const InstallOptions& options);
  // The trial is running and came up: it becomes the good version.
  [[nodiscard]] Expected<Outcome, std::string> confirm();
  // The trial failed: back to the good version. nothing_to_do when no trial is installed.
  [[nodiscard]] Expected<Outcome, std::string> rollback();

  [[nodiscard]] const std::optional<SlotState>& state() const noexcept { return state_; }
  [[nodiscard]] const std::string& current() const noexcept { return current_; }  // "a", "b" or ""
  // What open() repaired, for the log.
  [[nodiscard]] const std::vector<std::string>& repairs() const noexcept { return repairs_; }

 private:
  SlotStore() = default;
  Expected<void, std::string> write_state(const SlotState& s);
  Expected<void, std::string> switch_to(const std::string& slot);
  void step(std::string_view name) const;
  void log(std::string_view action, std::string_view version, std::string_view detail) const;

  std::filesystem::path root_;
  StepHook hook_;
  int lock_fd_ = -1;
  std::optional<SlotState> state_;
  std::string current_;
  std::vector<std::string> repairs_;
};

}  // namespace minidaq::update
