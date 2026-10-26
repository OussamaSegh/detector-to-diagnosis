// SPDX-License-Identifier: MIT
// Exercise 25.3: A/B slots that survive a power cut at any step. A model of the disk that
// minidaq_update works on, small enough to cut the power after every single write.
#pragma once

#include <array>
#include <cstddef>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace ab {

struct Slot {
  std::string version;   // what was extracted into the slot; empty: nothing
  bool checked = false;  // every file matches the slot's manifest
};

struct State {
  std::size_t good = 0;  // the slot of the last confirmed version
  std::string good_version;
  std::optional<std::size_t> trial;  // the slot of an installed version that is not yet confirmed
  std::string trial_version;
  bool operator==(const State&) const = default;
};

// What survives a power cut. Each write below is atomic, as a rename and a state file written to
// a temporary name and renamed are on a journaling file system: it happened entirely or not at
// all.
struct Disk {
  std::array<Slot, 2> slots;
  std::optional<std::size_t> current;  // the slot the link `current` points to; the one that runs
  std::optional<State> state;  // empty: nothing was ever installed
};

struct PowerCut : std::runtime_error {
  PowerCut() : std::runtime_error{"power cut"} {}
};

// The disk with its four writes. After `writes_before_cut` writes the power fails: the next write
// throws PowerCut and does not happen. A negative number: the power never fails.
class Machine {
 public:
  explicit Machine(Disk disk, int writes_before_cut = -1)
      : disk_{std::move(disk)}, left_{writes_before_cut} {}

  [[nodiscard]] const Disk& disk() const { return disk_; }
  [[nodiscard]] int writes() const { return writes_; }
  // Writes after which the running slot (current) was not a checked one: each is a moment when a
  // power cut would leave a system that cannot start. Must stay 0.
  [[nodiscard]] int unsafe_moments() const { return unsafe_; }

  // Replaces the slot's contents with the version's files, not yet checked.
  void extract(std::size_t slot, const std::string& version) {
    write();
    disk_.slots.at(slot) = Slot{version, false};
    after();
  }
  // Marks the slot's files as checked against its manifest.
  void check(std::size_t slot) {
    write();
    disk_.slots.at(slot).checked = !disk_.slots.at(slot).version.empty();
    after();
  }
  void write_state(const State& s) {
    write();
    disk_.state = s;
    after();
  }
  void switch_current(std::size_t slot) {
    write();
    disk_.current = slot;
    after();
  }

 private:
  void write() {
    if (left_ == 0) {
      throw PowerCut{};
    }
    --left_;
    ++writes_;
  }
  void after() {
    if (disk_.current && !disk_.slots.at(*disk_.current).checked) {
      ++unsafe_;
    }
  }
  Disk disk_;
  int left_;
  int writes_ = 0;
  int unsafe_ = 0;
};

// Installs `version` as a trial in the slot that does not hold the good version, and runs it; the
// very first installation is confirmed at once (there is nothing to go back to). Precondition: no
// trial (confirm or roll back first).
void install(Machine& m, const std::string& version);
// The trial becomes the good version. Nothing to do without a trial.
void confirm(Machine& m);
// The good version runs again and the trial is forgotten. Nothing to do without a trial.
void rollback(Machine& m);
// Called first after every start, before anything else: brings the disk back to a state that the
// three operations above can work from, and says what it changed. On return:
// - current is set if and only if state is set, and current is a checked slot;
// - current is the good slot or the trial slot, and a trial is always the current slot.
std::vector<std::string> repair(Machine& m);

}  // namespace ab
