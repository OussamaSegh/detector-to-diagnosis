// SPDX-License-Identifier: MIT
// minidaq_update: signed updates of MiniDAQ into two slots, with rollback (Chapter 25, ADR 0020).
//
//   minidaq_update install BUNDLE_DIR [--root /opt/minidaq] [--keys /etc/minidaq/update-keys]
//                  [--platform-file /etc/minidaq/platform-id] [--allow-older]
//   minidaq_update confirm  [--root DIR]   the trial version came up: keep it
//   minidaq_update rollback [--root DIR]   the trial version failed: back to the good one
//   minidaq_update status   [--root DIR]   the slots and the state, as JSON
//
// Installed by the platform image as /usr/lib/minidaq/minidaq_update, outside the slots, so that
// a broken update cannot break its own rollback. minidaq.service runs `confirm` after READY and
// minidaq-rollback.service runs `rollback` when the service has failed to start
// (packaging/systemd/). An install changes nothing that runs until the service restarts, which
// the update procedure does only when no acquisition is running.
//
// Exit status: 0 done; 1 error; 2 usage; 3 nothing to do (rollback without a trial, so that the
// unit that asked for it fails and nothing restarts a confirmed version that keeps failing).
#include <cstdio>
#include <exception>
#include <fstream>
#include <nlohmann/json.hpp>
#include <string>
#include <string_view>

#include "minidaq/update/slots.hpp"

namespace {

int usage(const char* argv0) {
  std::fprintf(stderr,
               "usage: %s install BUNDLE_DIR [--root DIR] [--keys DIR] [--platform-file FILE] "
               "[--allow-older]\n"
               "       %s confirm|rollback|status [--root DIR]\n",
               argv0, argv0);
  return 2;
}

int run(int argc, char** argv) {
  using namespace minidaq::update;
  if (argc < 2) {
    return usage(argv[0]);
  }
  const std::string_view command{argv[1]};
  std::string root = "/opt/minidaq";
  std::string bundle;
  std::string platform_file = "/etc/minidaq/platform-id";
  InstallOptions options;
  options.keys_dir = "/etc/minidaq/update-keys";
  int i = 2;
  if (command == "install") {
    if (argc < 3) {
      return usage(argv[0]);
    }
    bundle = argv[2];
    i = 3;
  } else if (command != "confirm" && command != "rollback" && command != "status") {
    return usage(argv[0]);
  }
  for (; i < argc; ++i) {
    const std::string_view a{argv[i]};
    if (a == "--allow-older" && command == "install") {
      options.allow_older = true;
      continue;
    }
    const char* v = i + 1 < argc ? argv[++i] : nullptr;
    if (a == "--root" && v) {
      root = v;
    } else if (a == "--keys" && v && command == "install") {
      options.keys_dir = v;
    } else if (a == "--platform-file" && v && command == "install") {
      platform_file = v;
    } else {
      return usage(argv[0]);
    }
  }

  auto store = SlotStore::open(root);
  if (!store) {
    std::fprintf(stderr, "minidaq_update: %s\n", store.error().c_str());
    return 1;
  }
  for (const auto& r : store->repairs()) {
    std::printf("minidaq_update: repaired: %s\n", r.c_str());
  }

  if (command == "install") {
    std::ifstream in{platform_file};
    std::getline(in, options.platform);
    if (!in || options.platform.empty()) {
      std::fprintf(stderr, "minidaq_update: cannot read this PC's platform from %s\n",
                   platform_file.c_str());
      return 1;
    }
    auto r = store->install(bundle, options);
    if (!r) {
      std::fprintf(stderr, "minidaq_update: install refused: %s\n", r.error().c_str());
      return 1;
    }
    std::printf("minidaq_update: installed %s\n", r->c_str());
    return 0;
  }
  if (command == "confirm" || command == "rollback") {
    auto r = command == "confirm" ? store->confirm() : store->rollback();
    if (!r) {
      std::fprintf(stderr, "minidaq_update: %s failed: %s\n", argv[1], r.error().c_str());
      return 1;
    }
    if (*r == Outcome::nothing_to_do) {
      std::printf("minidaq_update: %s: no trial version installed\n", argv[1]);
      return command == "rollback" ? 3 : 0;
    }
    const auto& st = *store->state();
    std::printf("minidaq_update: %s: version %s in slot %s runs\n", argv[1],
                st.good_version.c_str(), st.good.c_str());
    return 0;
  }
  nlohmann::json j{{"root", root}, {"current", store->current()}};
  if (const auto& st = store->state(); st) {
    j["good"] = {{"slot", st->good}, {"version", st->good_version}};
    j["trial"] = st->trial ? nlohmann::json{{"slot", *st->trial}, {"version", st->trial_version}}
                           : nlohmann::json(nullptr);
  }
  std::printf("%s\n", j.dump(2).c_str());
  return 0;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    return run(argc, argv);
  } catch (const std::exception& e) {  // e.g. std::bad_alloc, or a filesystem error not foreseen
    std::fprintf(stderr, "minidaq_update: %s\n", e.what());
    return 1;
  }
}
