// SPDX-License-Identifier: MIT
#include "minidaq/rt/realtime.hpp"

#include <pthread.h>
#include <sched.h>
#include <sys/mman.h>
#include <sys/prctl.h>
#include <sys/resource.h>

#include <algorithm>
#include <cerrno>
#include <charconv>
#include <cstring>

namespace minidaq::rt {
namespace {

constexpr std::array<std::string_view, max_stages> stage_names{"source", "decode", "sort", "pair", "write"};

std::error_code errno_code(int e) noexcept { return {e, std::generic_category()}; }

std::string_view trim(std::string_view s) noexcept {
  while (!s.empty() && (s.front() == ' ' || s.front() == '\t' || s.front() == '\r')) {
    s.remove_prefix(1);
  }
  while (!s.empty() && (s.back() == ' ' || s.back() == '\t' || s.back() == '\r')) {
    s.remove_suffix(1);
  }
  return s;
}

bool parse_int(std::string_view s, int& out) noexcept {
  const auto r = std::from_chars(s.data(), s.data() + s.size(), out);
  return r.ec == std::errc{} && r.ptr == s.data() + s.size();
}

}  // namespace

std::string_view to_string(SchedPolicy p) noexcept {
  switch (p) {
    case SchedPolicy::other:
      return "other";
    case SchedPolicy::fifo:
      return "fifo";
    case SchedPolicy::rr:
      return "rr";
  }
  return "?";
}

// [snippet:pin]
Expected<void, std::error_code> pin_current_thread(int cpu) noexcept {
  if (cpu < 0 || cpu >= CPU_SETSIZE) {
    return Unexpected{errno_code(EINVAL)};
  }
  cpu_set_t set;
  CPU_ZERO(&set);
  CPU_SET(static_cast<unsigned>(cpu), &set);
  // pthread_* functions return the error number instead of setting errno.
  if (const int rc = pthread_setaffinity_np(pthread_self(), sizeof(set), &set); rc != 0) {
    return Unexpected{errno_code(rc)};
  }
  return {};
}
// [/snippet:pin]

// [snippet:sched]
Expected<void, std::error_code> set_current_thread_scheduler(SchedPolicy policy, int priority) noexcept {
  int native = SCHED_OTHER;
  sched_param param{};
  if (policy == SchedPolicy::fifo || policy == SchedPolicy::rr) {
    native = policy == SchedPolicy::fifo ? SCHED_FIFO : SCHED_RR;
    const int lo = sched_get_priority_min(native);
    const int hi = sched_get_priority_max(native);
    if (priority < lo || priority > hi) {
      return Unexpected{errno_code(EINVAL)};
    }
    param.sched_priority = priority;
  }
  if (const int rc = pthread_setschedparam(pthread_self(), native, &param); rc != 0) {
    return Unexpected{errno_code(rc)};  // typically EPERM without CAP_SYS_NICE
  }
  return {};
}
// [/snippet:sched]

void name_current_thread(std::string_view name) noexcept {
  char buf[16]{};  // Linux limit: 15 characters plus the terminator
  const std::size_t n = std::min(name.size(), sizeof(buf) - 1);
  std::memcpy(buf, name.data(), n);
  (void)pthread_setname_np(pthread_self(), buf);
}

int current_cpu() noexcept { return sched_getcpu(); }

Expected<void, std::error_code> set_timer_slack_ns(unsigned long ns) noexcept {
  if (prctl(PR_SET_TIMERSLACK, ns, 0, 0, 0) != 0) {
    return Unexpected{errno_code(errno)};
  }
  return {};
}

// [snippet:prefault]
void prefault_stack(std::size_t bytes) noexcept {
  // Touch one byte per 4 KiB page of a stack buffer, from a separate frame,
  // so the kernel maps those pages now rather than on first use in the hot
  // path. With mlockall(MCL_FUTURE) they then stay resident.
  constexpr std::size_t chunk = std::size_t{64} * 1024;
  volatile unsigned char buf[chunk];  // volatile: the stores must happen
  if (bytes > chunk) {
    prefault_stack(bytes - chunk);  // deeper pages first; not a tail call,
  }                                 // so each level keeps its own frame
  for (std::size_t i = 0; i < sizeof(buf); i += 4096) {
    buf[i] = 0;
  }
}
// [/snippet:prefault]

StageRtStatus apply_stage(const StageRt& s, std::size_t prefault_bytes) noexcept {
  StageRtStatus st;
  st.applied = true;
  st.requested_cpu = s.cpu;
  if (s.cpu >= 0) {
    if (auto r = pin_current_thread(s.cpu); r) {
      st.pinned = true;
    } else {
      st.error = r.error();
    }
  }
  if (auto r = set_current_thread_scheduler(s.policy, s.priority); r) {
    st.scheduled = true;
  } else if (!st.error) {
    st.error = r.error();
  }
  if (prefault_bytes > 0) {
    prefault_stack(prefault_bytes);
  }
  st.running_cpu = current_cpu();
  return st;
}

// [snippet:mlock]
Expected<void, std::error_code> lock_all_memory() noexcept {
  // MCL_CURRENT locks what is mapped now; MCL_FUTURE everything mapped later
  // (new heap, thread stacks). Needs CAP_IPC_LOCK or a large RLIMIT_MEMLOCK.
  if (mlockall(MCL_CURRENT | MCL_FUTURE) != 0) {
    return Unexpected{errno_code(errno)};
  }
  return {};
}
// [/snippet:mlock]

PageFaults thread_page_faults() noexcept {
  rusage u{};
  if (getrusage(RUSAGE_THREAD, &u) != 0) {
    return {};
  }
  return {u.ru_minflt, u.ru_majflt};  // NOLINT(cppcoreguidelines-pro-type-union-access): glibc wraps rusage fields in unions
}

Expected<RtProfile, ProfileError> parse_profile(std::string_view text) {
  RtProfile p;
  int line_no = 0;
  while (!text.empty()) {
    ++line_no;
    const auto nl = text.find('\n');
    std::string_view line = text.substr(0, nl);
    text = nl == std::string_view::npos ? std::string_view{} : text.substr(nl + 1);
    if (const auto hash = line.find('#'); hash != std::string_view::npos) {
      line = line.substr(0, hash);
    }
    line = trim(line);
    if (line.empty()) {
      continue;
    }
    const auto eq = line.find('=');
    if (eq == std::string_view::npos) {
      return Unexpected{ProfileError{line_no, "expected key = value"}};
    }
    const std::string_view key = trim(line.substr(0, eq));
    const std::string_view value = trim(line.substr(eq + 1));
    auto bad = [&](std::string_view what) {
      return Unexpected{ProfileError{line_no, std::string{what} + ": '" + std::string{value} + "'"}};
    };
    if (key == "lock_memory") {
      if (value != "true" && value != "false") {
        return bad("lock_memory must be true or false");
      }
      p.lock_memory = value == "true";
      continue;
    }
    if (key == "prefault_stack_kib") {
      int kib = 0;
      if (!parse_int(value, kib) || kib < 0 || kib > 65536) {
        return bad("prefault_stack_kib must be 0..65536");
      }
      p.prefault_stack_bytes = static_cast<std::size_t>(kib) * 1024;
      continue;
    }
    const auto dot = key.find('.');
    // NOLINTNEXTLINE(readability-qualified-auto): a pointer only in some standard libraries
    const auto it = std::find(stage_names.begin(), stage_names.end(), key.substr(0, dot));
    if (dot == std::string_view::npos || it == stage_names.end()) {
      return Unexpected{ProfileError{line_no, "unknown key '" + std::string{key} + "'"}};
    }
    StageRt& s = p.stages[static_cast<std::size_t>(it - stage_names.begin())];
    const std::string_view field = key.substr(dot + 1);
    if (field == "cpu") {
      if (!parse_int(value, s.cpu) || s.cpu < -1) {
        return bad("cpu must be -1 or a CPU number");
      }
    } else if (field == "policy") {
      if (value == "other") {
        s.policy = SchedPolicy::other;
      } else if (value == "fifo") {
        s.policy = SchedPolicy::fifo;
      } else if (value == "rr") {
        s.policy = SchedPolicy::rr;
      } else {
        return bad("policy must be other, fifo or rr");
      }
    } else if (field == "priority") {
      if (!parse_int(value, s.priority) || s.priority < 0 || s.priority > 99) {
        return bad("priority must be 0..99");
      }
    } else {
      return Unexpected{ProfileError{line_no, "unknown key '" + std::string{key} + "'"}};
    }
  }
  for (const StageRt& s : p.stages) {
    if (s.policy != SchedPolicy::other && s.priority == 0) {
      return Unexpected{ProfileError{0, "fifo/rr stages need a priority of 1..99"}};
    }
  }
  return p;
}

std::string format_profile(const RtProfile& p) {
  std::string out;
  out += "lock_memory = " + std::string{p.lock_memory ? "true" : "false"} + "\n";
  out += "prefault_stack_kib = " + std::to_string(p.prefault_stack_bytes / 1024) + "\n";
  for (std::size_t i = 0; i < max_stages; ++i) {
    const StageRt& s = p.stages[i];
    const std::string n{stage_names[i]};
    out += n + ".cpu = " + std::to_string(s.cpu) + "\n";
    out += n + ".policy = " + std::string{to_string(s.policy)} + "\n";
    out += n + ".priority = " + std::to_string(s.priority) + "\n";
  }
  return out;
}

}  // namespace minidaq::rt
