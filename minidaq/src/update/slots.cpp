// SPDX-License-Identifier: MIT
#include "minidaq/update/slots.hpp"

#include <fcntl.h>
#include <spawn.h>
#include <sys/file.h>
#include <sys/wait.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <cerrno>
#include <chrono>
#include <cstring>
#include <ctime>
#include <fstream>
#include <map>
#include <nlohmann/json.hpp>
#include <sstream>
#include <utility>

namespace minidaq::update {

namespace fs = std::filesystem;
using nlohmann::json;

namespace {

constexpr const char* tar_program = "/usr/bin/tar";  // an absolute path: no PATH to hijack

std::string errno_text(int e) { return std::system_category().message(e); }

std::string other(const std::string& slot) { return slot == "a" ? "b" : "a"; }

std::string utc_now() {
  const auto t = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
  std::tm tm{};
  (void)gmtime_r(&t, &tm);
  std::array<char, 32> buf{};
  (void)std::strftime(buf.data(), buf.size(), "%Y-%m-%dT%H:%M:%SZ", &tm);
  return buf.data();
}

// fsync of a file or a directory by path; 0 or an errno.
int sync_path(const fs::path& p, bool directory) {
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg): open(2) is variadic
  const int fd = ::open(p.c_str(), (directory ? O_RDONLY | O_DIRECTORY : O_RDONLY) | O_CLOEXEC);
  if (fd < 0) {
    return errno;
  }
  const int r = ::fsync(fd) == 0 ? 0 : errno;
  ::close(fd);
  return r;
}

// Writes `text` to `path` so that a reader finds the old content or the new, never a mix:
// a temporary file, fsync, rename over the old one, fsync of the directory.
Expected<void, std::string> write_atomically(const fs::path& path, const std::string& text) {
  const fs::path tmp = path.string() + ".tmp";
  {
    std::ofstream out{tmp, std::ios::binary | std::ios::trunc};
    out << text;
    out.close();
    if (!out) {
      return Unexpected{"cannot write " + tmp.string()};
    }
  }
  if (const int e = sync_path(tmp, false); e != 0) {
    return Unexpected{"cannot sync " + tmp.string() + ": " + errno_text(e)};
  }
  if (::rename(tmp.c_str(), path.c_str()) != 0) {
    return Unexpected{"cannot rename " + tmp.string() + ": " + errno_text(errno)};
  }
  if (const int e = sync_path(path.parent_path(), true); e != 0) {
    return Unexpected{"cannot sync " + path.parent_path().string() + ": " + errno_text(e)};
  }
  return {};
}

// [snippet:spawn]
// Runs tar with `args`; its standard output, if `out` is given, is collected there.
Expected<void, std::string> run_tar(std::vector<std::string> args, std::string* out) {
  args.insert(args.begin(), "tar");
  std::vector<char*> argv;
  argv.reserve(args.size() + 1);
  // cppcheck-suppress constVariableReference ; posix_spawn takes char*
  for (auto& a : args) {
    argv.push_back(a.data());
  }
  argv.push_back(nullptr);
  std::array<char, 9> lc_all{"LC_ALL=C"};
  std::array<char*, 2> envp{lc_all.data(), nullptr};  // nothing of the caller's environment

  std::array<int, 2> pipe_fds{-1, -1};
  if (out != nullptr && ::pipe2(pipe_fds.data(), O_CLOEXEC) != 0) {
    return Unexpected{"pipe: " + errno_text(errno)};
  }
  posix_spawn_file_actions_t actions;
  posix_spawn_file_actions_init(&actions);
  if (out != nullptr) {
    posix_spawn_file_actions_adddup2(&actions, pipe_fds[1], STDOUT_FILENO);
  }
  pid_t pid = -1;
  const int spawned = ::posix_spawn(&pid, tar_program, &actions, nullptr, argv.data(), envp.data());
  posix_spawn_file_actions_destroy(&actions);
  if (out != nullptr) {
    ::close(pipe_fds[1]);
    if (spawned == 0) {
      std::array<char, 4096> buf{};
      ssize_t n = 0;
      while ((n = ::read(pipe_fds[0], buf.data(), buf.size())) > 0 || (n < 0 && errno == EINTR)) {
        if (n > 0) {
          out->append(buf.data(), static_cast<std::size_t>(n));
        }
      }
    }
    ::close(pipe_fds[0]);
  }
  if (spawned != 0) {
    return Unexpected{std::string{"cannot run "} + tar_program + ": " + errno_text(spawned)};
  }
  int status = 0;
  while (::waitpid(pid, &status, 0) < 0) {
    if (errno != EINTR) {
      return Unexpected{"waitpid: " + errno_text(errno)};
    }
  }
  if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
    return Unexpected{std::string{"tar "} + args[1] + " failed (status " + std::to_string(status) +
                      ")"};
  }
  return {};
}
// [/snippet:spawn]

std::string normal(std::string name) {
  if (name.starts_with("./")) {
    name.erase(0, 2);
  }
  while (!name.empty() && name.back() == '/') {
    name.pop_back();
  }
  return name;
}

// A path from an archive or a manifest that stays inside the directory it is relative to. The
// directory itself ("./", as tar lists it) is inside.
bool contained(const std::string& raw) {
  if (raw.empty() || raw.front() == '/') {
    return false;
  }
  const std::string name = normal(raw);
  if (name.empty() || name == ".") {
    return true;
  }
  return std::ranges::none_of(fs::path{name}, [](const fs::path& part) { return part == ".."; });
}

}  // namespace

// [snippet:tree]
Expected<std::size_t, std::string> verify_tree(const fs::path& slot) {
  std::ifstream in{slot / "MANIFEST.sha256"};
  if (!in) {
    return Unexpected{std::string{"no MANIFEST.sha256 in the archive"}};
  }
  std::map<std::string, std::string> listed;  // path -> digest, as sha256sum(1) writes them
  std::string line;
  while (std::getline(in, line)) {
    if (line.size() < 67 || line[64] != ' ' || (line[65] != ' ' && line[65] != '*')) {
      return Unexpected{"MANIFEST.sha256: not \"DIGEST  PATH\": " + line.substr(0, 80)};
    }
    std::string path = normal(line.substr(66));
    if (!contained(path) || path.empty() || path == "." || path == "MANIFEST.sha256" ||
        !listed.emplace(path, line.substr(0, 64)).second) {
      return Unexpected{"MANIFEST.sha256: bad or repeated path \"" + path + "\""};
    }
  }
  std::size_t files = 0;
  std::error_code ec;
  for (auto it = fs::recursive_directory_iterator{slot, ec};
       !ec && it != fs::recursive_directory_iterator{}; it.increment(ec)) {
    const auto rel = fs::relative(it->path(), slot).generic_string();
    const auto type = it->symlink_status().type();
    if (type == fs::file_type::directory) {
      continue;
    }
    if (type != fs::file_type::regular) {
      return Unexpected{rel + " is not a regular file or a directory"};
    }
    if (rel == "MANIFEST.sha256") {
      continue;
    }
    const auto entry = listed.find(rel);
    if (entry == listed.end()) {
      return Unexpected{rel + " is not in MANIFEST.sha256"};
    }
    const auto d = digest_file(it->path());
    if (!d || d->sha256 != entry->second) {
      return Unexpected{rel + " does not match its digest in MANIFEST.sha256"};
    }
    ++files;
  }
  if (ec) {
    return Unexpected{"cannot read " + slot.string() + ": " + ec.message()};
  }
  if (files != listed.size()) {
    return Unexpected{std::to_string(listed.size() - files) +
                      " files of MANIFEST.sha256 are missing"};
  }
  return files;
}
// [/snippet:tree]

SlotStore::~SlotStore() {
  if (lock_fd_ >= 0) {
    ::close(lock_fd_);  // releases the lock
  }
}

SlotStore::SlotStore(SlotStore&& other) noexcept
    : root_{std::move(other.root_)},
      hook_{std::move(other.hook_)},
      lock_fd_{std::exchange(other.lock_fd_, -1)},
      state_{std::move(other.state_)},
      current_{std::move(other.current_)},
      repairs_{std::move(other.repairs_)} {}

SlotStore& SlotStore::operator=(SlotStore&& other) noexcept {
  if (this != &other) {
    if (lock_fd_ >= 0) {
      ::close(lock_fd_);
    }
    root_ = std::move(other.root_);
    hook_ = std::move(other.hook_);
    lock_fd_ = std::exchange(other.lock_fd_, -1);
    state_ = std::move(other.state_);
    current_ = std::move(other.current_);
    repairs_ = std::move(other.repairs_);
  }
  return *this;
}

void SlotStore::step(std::string_view name) const {
  if (hook_) {
    hook_(name);
  }
}

void SlotStore::log(std::string_view action, std::string_view version,
                    std::string_view detail) const {
  // The store's own record of what was installed when, next to the slots. Best effort: the
  // state file, not this log, decides what runs.
  std::ofstream out{root_ / "history.jsonl", std::ios::app};
  out << json{{"time", utc_now()}, {"action", action}, {"version", version}, {"detail", detail}}
             .dump()
      << '\n';
  out.close();
  (void)sync_path(root_ / "history.jsonl", false);
}

Expected<void, std::string> SlotStore::write_state(const SlotState& s) {
  const json j{{"good", s.good},
               {"good_version", s.good_version},
               {"trial", s.trial ? json(*s.trial) : json(nullptr)},
               {"trial_version", s.trial_version}};
  auto w = write_atomically(root_ / "state.json", j.dump(2) + "\n");
  if (w) {
    state_ = s;
  }
  return w;
}

// [snippet:switch]
Expected<void, std::string> SlotStore::switch_to(const std::string& slot) {
  const fs::path link = root_ / "current";
  const fs::path next = root_ / "current.new";
  std::error_code ec;
  fs::remove(next, ec);
  fs::create_directory_symlink(fs::path{"slots"} / slot, next, ec);
  if (ec) {
    return Unexpected{"cannot make " + next.string() + ": " + ec.message()};
  }
  // rename(2) replaces `current` atomically: there is no instant without it.
  if (::rename(next.c_str(), link.c_str()) != 0) {
    return Unexpected{"cannot switch " + link.string() + ": " + errno_text(errno)};
  }
  if (const int e = sync_path(root_, true); e != 0) {
    return Unexpected{"cannot sync " + root_.string() + ": " + errno_text(e)};
  }
  current_ = slot;
  return {};
}
// [/snippet:switch]

// [snippet:open]
Expected<SlotStore, std::string> SlotStore::open(fs::path root, StepHook hook) {
  SlotStore s;
  s.root_ = std::move(root);
  s.hook_ = std::move(hook);
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg): open(2) is variadic
  s.lock_fd_ = ::open((s.root_ / "lock").c_str(), O_RDWR | O_CREAT | O_CLOEXEC, 0600);
  if (s.lock_fd_ < 0) {
    return Unexpected{"cannot open " + (s.root_ / "lock").string() + ": " + errno_text(errno)};
  }
  if (::flock(s.lock_fd_, LOCK_EX | LOCK_NB) != 0) {
    return Unexpected{"another minidaq_update is running on " + s.root_.string()};
  }
  std::error_code ec;
  fs::remove(s.root_ / "current.new", ec);  // a switch cut short; `current` is still whole
  fs::remove(s.root_ / "state.json.tmp", ec);

  std::ifstream in{s.root_ / "state.json"};
  if (in) {
    const auto j = json::parse(in, nullptr, false);
    if (!j.is_object() || !j.contains("good") || !j["good"].is_string() || !j.contains("trial")) {
      return Unexpected{"state.json is damaged: a person must look at " + s.root_.string()};
    }
    SlotState st;
    st.good = j["good"].get<std::string>();
    st.good_version = j.value("good_version", "");
    if (j["trial"].is_string()) {
      st.trial = j["trial"].get<std::string>();
    }
    st.trial_version = j.value("trial_version", "");
    s.state_ = st;
  }
  const auto target = fs::read_symlink(s.root_ / "current", ec);
  if (!ec) {
    const auto t = target.generic_string();
    s.current_ = t == "slots/a" ? "a" : t == "slots/b" ? "b" : "";
    if (s.current_.empty()) {
      return Unexpected{"current points to " + t + ", not to a slot"};
    }
  }
  if (!s.state_) {
    if (!s.current_.empty()) {
      return Unexpected{std::string{"current exists without state.json: a person must look"}};
    }
    return s;  // nothing installed yet
  }
  if (s.current_.empty()) {  // a first installation cut before its switch
    if (auto w = s.switch_to(s.state_->good); !w) {
      return Unexpected{w.error()};
    }
    s.repairs_.push_back("current restored to the confirmed slot " + s.state_->good);
  }
  if (s.state_->trial && s.current_ != *s.state_->trial) {
    // An install cut before its switch, or a rollback cut after it: the trial never ran, or
    // has already been left. Either way it is no longer a trial.
    SlotState st = *s.state_;
    s.repairs_.push_back("trial " + st.trial_version + " in slot " + *st.trial +
                         " discarded: it is not current");
    st.trial.reset();
    st.trial_version.clear();
    if (auto w = s.write_state(st); !w) {
      return Unexpected{w.error()};
    }
  }
  if (s.current_ != s.state_->good && s.current_ != s.state_->trial.value_or("")) {
    return Unexpected{"current is slot " + s.current_ +
                      ", which is neither the good version nor a trial"};
  }
  for (const auto& r : s.repairs_) {
    s.log("repair", "", r);
  }
  return s;
}
// [/snippet:open]

// [snippet:install]
Expected<std::string, std::string> SlotStore::install(const fs::path& bundle_dir,
                                                      const InstallOptions& options) {
  if (state_ && state_->trial) {
    return Unexpected{"version " + state_->trial_version +
                      " is installed and not confirmed: confirm or roll back first"};
  }
  auto signed_manifest = read_signed_manifest(bundle_dir, options.keys_dir);
  if (!signed_manifest) {
    return Unexpected{signed_manifest.error()};
  }
  const Manifest& m = signed_manifest->manifest;
  if (m.product != "minidaq") {
    return Unexpected{"the bundle is for \"" + m.product + "\", not minidaq"};
  }
  if (m.platform != options.platform) {
    return Unexpected{"the bundle is for the platform \"" + m.platform + "\"; this PC is \"" +
                      options.platform + "\""};
  }
  if (state_ && !options.allow_older) {
    const auto good = Version::parse(state_->good_version);
    if (good && m.version <= *good) {
      return Unexpected{"version " + m.version.str() + " is not newer than the installed " +
                        good->str() + " (a downgrade must be asked for)"};
    }
  }
  const fs::path archive = bundle_dir / m.archive;
  const auto digest = digest_file(archive);
  if (!digest || digest->size != m.size || digest->sha256 != m.sha256) {
    return Unexpected{m.archive + " is not the archive the manifest describes"};
  }
  step("verified");

  const std::string slot = state_ ? other(current_) : "a";
  const fs::path dir = root_ / "slots" / slot;
  std::error_code ec;
  fs::remove_all(dir, ec);
  fs::create_directories(dir, ec);
  if (ec) {
    return Unexpected{"cannot prepare " + dir.string() + ": " + ec.message()};
  }
  std::string names;
  if (auto listed = run_tar({"--list", "--gzip", "--file", archive.string()}, &names); !listed) {
    return Unexpected{listed.error()};
  }
  std::istringstream lines{names};
  for (std::string name; std::getline(lines, name);) {
    if (!contained(name)) {
      return Unexpected{"the archive holds \"" + name + "\", outside its directory"};
    }
  }
  if (auto x = run_tar({"--extract", "--gzip", "--file", archive.string(), "--directory",
                        dir.string(), "--no-same-owner", "--no-same-permissions"},
                       nullptr);
      !x) {
    return Unexpected{x.error()};
  }
  step("extracted");
  const auto files = verify_tree(dir);
  if (!files) {
    return Unexpected{"slot " + slot + ": " + files.error()};
  }
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg): open(2) is variadic
  if (const int fd = ::open(dir.c_str(), O_RDONLY | O_DIRECTORY | O_CLOEXEC); fd >= 0) {
    (void)::syncfs(fd);  // the slot's files on disk before anything points to them
    ::close(fd);
  }
  step("checked");

  SlotState next = state_.value_or(SlotState{});
  if (state_) {
    next.trial = slot;
    next.trial_version = m.version.str();
  } else {  // the first installation: nothing to go back to, so nothing to try
    next.good = slot;
    next.good_version = m.version.str();
  }
  if (auto w = write_state(next); !w) {
    return Unexpected{w.error()};
  }
  step("recorded");
  if (auto w = switch_to(slot); !w) {
    return Unexpected{w.error()};
  }
  step("switched");
  std::string summary = "version " + m.version.str() + " (" + m.commit + ") in slot " + slot +
                        ", " + std::to_string(*files) + " files, signed with " +
                        signed_manifest->key +
                        (next.trial ? "; a trial until it is confirmed" : "; confirmed");
  log("install", m.version.str(), summary);
  return summary;
}
// [/snippet:install]

// [snippet:confirm]
Expected<Outcome, std::string> SlotStore::confirm() {
  if (!state_ || !state_->trial) {
    return Outcome::nothing_to_do;
  }
  SlotState next = *state_;
  next.good = *next.trial;
  next.good_version = next.trial_version;
  next.trial.reset();
  next.trial_version.clear();
  if (auto w = write_state(next); !w) {
    return Unexpected{w.error()};
  }
  step("recorded");
  log("confirm", next.good_version, "slot " + next.good);
  return Outcome::done;
}

Expected<Outcome, std::string> SlotStore::rollback() {
  if (!state_ || !state_->trial) {
    return Outcome::nothing_to_do;
  }
  const std::string failed = state_->trial_version;
  // The switch first: cut after it, open() finds a trial that is not current and discards it,
  // which completes the rollback. The other order could leave the failed version current.
  if (auto w = switch_to(state_->good); !w) {
    return Unexpected{w.error()};
  }
  step("switched");
  SlotState next = *state_;
  next.trial.reset();
  next.trial_version.clear();
  if (auto w = write_state(next); !w) {
    return Unexpected{w.error()};
  }
  step("recorded");
  log("rollback", failed, "back to " + next.good_version + " in slot " + next.good);
  return Outcome::done;
}
// [/snippet:confirm]

}  // namespace minidaq::update
