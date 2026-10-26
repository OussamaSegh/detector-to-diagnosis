// SPDX-License-Identifier: MIT
#include "minidaq/rt/crash_report.hpp"

#include <elf.h>
#include <link.h>
#include <sys/syscall.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cerrno>
#include <cstddef>
#include <cstdint>
#include <cstring>

#include "minidaq/core/flight_recorder.hpp"

namespace minidaq::rt {
namespace {

constexpr std::array fatal_signals{SIGSEGV, SIGBUS, SIGFPE, SIGILL, SIGABRT};
constexpr std::size_t kReportEvents = 64;  // the last events written into the report

// Prepared by install_crash_report(), read by the handler.
// NOLINTBEGIN(cppcoreguidelines-avoid-non-const-global-variables)
int report_fd = -1;
std::array<char, 64> version_text{};
std::size_t version_size = 0;
std::array<char, 2 * 64 + 1> build_id_hex{};
std::size_t build_id_size = 0;
std::array<std::byte, std::size_t{64} * 1024> alt_stack{};
std::array<TraceEvent, kReportEvents> report_events{};
std::atomic<bool> reporting{false};
// NOLINTEND(cppcoreguidelines-avoid-non-const-global-variables)

// A buffered writer for the handler: no allocation, write(2) only.
class Out {
 public:
  explicit Out(int fd) noexcept : fd_(fd) {}
  Out(const Out&) = delete;
  Out& operator=(const Out&) = delete;
  Out(Out&&) = delete;
  Out& operator=(Out&&) = delete;
  ~Out() { flush(); }

  Out& str(std::string_view s) noexcept {
    for (const char c : s) {
      put(c);
    }
    return *this;
  }
  Out& dec(std::uint64_t v) noexcept {
    std::array<char, 20> d{};
    std::size_t n = 0;
    do {
      d[n++] = static_cast<char>('0' + v % 10);
      v /= 10;
    } while (v != 0);
    while (n > 0) {
      put(d[--n]);
    }
    return *this;
  }
  Out& hex(std::uint64_t v) noexcept {
    str("0x");
    bool started = false;
    for (int shift = 60; shift >= 0; shift -= 4) {
      const auto digit = static_cast<unsigned>((v >> shift) & 0xFU);
      if (digit != 0 || started || shift == 0) {
        put("0123456789abcdef"[digit]);
        started = true;
      }
    }
    return *this;
  }
  void flush() noexcept {
    std::size_t done = 0;
    while (done < n_ && fd_ >= 0) {
      const ssize_t w = ::write(fd_, buf_.data() + done, n_ - done);
      if (w < 0 && errno == EINTR) {
        continue;
      }
      if (w <= 0) {
        break;  // nothing more we can do while dying
      }
      done += static_cast<std::size_t>(w);
    }
    n_ = 0;
  }

 private:
  void put(char c) noexcept {
    if (n_ == buf_.size()) {
      flush();
    }
    buf_[n_++] = c;
  }
  int fd_;
  std::array<char, 512> buf_{};
  std::size_t n_ = 0;
};

// [snippet:handler]
// cppcheck-suppress constParameterCallback ; sigaction fixes the signature
void on_fatal_signal(int sig, siginfo_t* info, void* /*context*/) noexcept {
  // SA_RESETHAND has already restored the default action, so a second fault, in this handler
  // or in another thread, ends the process. Only the first thread to get here writes.
  if (!reporting.exchange(true)) {
    const int saved_errno = errno;
    write_crash_report(report_fd, sig, info);
    errno = saved_errno;
  }
  // The default action again: a fault re-executes the instruction when the handler returns and
  // faults again, killed this time; a signal that was sent (abort, kill) is sent once more.
  // Either way the core dump shows the thread as it was at the fault.
  if (info == nullptr || info->si_code <= 0) {  // sent by kill, raise or abort
    (void)::raise(sig);
  }
}
// [/snippet:handler]

// The notes are read where the loader mapped them: addresses from the program headers, turned
// into pointers. That is what dl_iterate_phdr is for, so the casts are the point here.
// NOLINTBEGIN(cppcoreguidelines-pro-type-reinterpret-cast, performance-no-int-to-ptr)
int read_build_id(dl_phdr_info* info, std::size_t /*size*/, void* /*data*/) noexcept {
  // The first object is the program itself; its name is empty.
  for (std::size_t i = 0; i < info->dlpi_phnum; ++i) {
    const auto& ph = info->dlpi_phdr[i];
    if (ph.p_type != PT_NOTE) {
      continue;
    }
    auto at = static_cast<std::uintptr_t>(info->dlpi_addr + ph.p_vaddr);
    const std::uintptr_t end = at + ph.p_memsz;
    while (at + sizeof(ElfW(Nhdr)) <= end) {
      ElfW(Nhdr) note{};
      std::memcpy(&note, reinterpret_cast<const void*>(at), sizeof note);
      const std::uintptr_t name = at + sizeof note;
      const std::uintptr_t desc = name + ((note.n_namesz + 3U) & ~3U);
      if (note.n_type == NT_GNU_BUILD_ID && note.n_namesz == 4 &&
          std::memcmp(reinterpret_cast<const void*>(name), "GNU", 4) == 0) {
        const auto* bytes = reinterpret_cast<const unsigned char*>(desc); 
        const std::size_t n = std::min<std::size_t>(note.n_descsz, (build_id_hex.size() - 1) / 2);
        for (std::size_t k = 0; k < n; ++k) {
          build_id_hex[2 * k] = "0123456789abcdef"[bytes[k] >> 4];
          build_id_hex[2 * k + 1] = "0123456789abcdef"[bytes[k] & 0xFU];
        }
        build_id_size = 2 * n;
        return 1;
      }
      at = desc + ((note.n_descsz + 3U) & ~3U);
    }
  }
  return 1;  // only the program: stop after the first object
}
// NOLINTEND(cppcoreguidelines-pro-type-reinterpret-cast, performance-no-int-to-ptr)

void load_build_id() noexcept {
  static std::atomic<bool> loaded{false};
  if (!loaded.exchange(true)) {
    (void)dl_iterate_phdr(read_build_id, nullptr);
  }
}

// Read at start-up, before main: a report written without install_crash_report() (a test, the
// diagnostics command) has the build ID too, and the handler never calls dl_iterate_phdr,
// which is not async-signal-safe.
[[maybe_unused]] const bool build_id_loaded = (load_build_id(), true);

}  // namespace

std::string_view signal_name(int sig) noexcept {
  switch (sig) {
    case SIGSEGV:
      return "SIGSEGV";
    case SIGBUS:
      return "SIGBUS";
    case SIGFPE:
      return "SIGFPE";
    case SIGILL:
      return "SIGILL";
    case SIGABRT:
      return "SIGABRT";
    default:
      return "signal";
  }
}

std::string_view build_id() noexcept {
  load_build_id();
  return {build_id_hex.data(), build_id_size};
}

// [snippet:report]
void write_crash_report(int fd, int sig, const siginfo_t* info) noexcept {
  Out out{fd};
  out.str("MiniDAQ crash report\n");
  out.str("signal: ").str(signal_name(sig)).str(" (").dec(static_cast<std::uint64_t>(sig)).str(")");
  if (info != nullptr) {
    if (info->si_code <= 0) {
      // Sent by kill, raise or abort: si_addr means nothing then, the sender is what counts.
      out.str(" sent by pid ").dec(static_cast<std::uint64_t>(info->si_pid));
    } else {
      out.str(" code ").dec(static_cast<std::uint64_t>(info->si_code));
      // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast): the address as a number
      out.str(" address ").hex(reinterpret_cast<std::uintptr_t>(info->si_addr));
    }
  }
  out.str("\nversion: ").str({version_text.data(), version_size});
  out.str("\nbuild-id: ").str({build_id_hex.data(), build_id_size});
  out.str("\npid: ").dec(static_cast<std::uint64_t>(::getpid()));
  out.str(" thread: ").dec(static_cast<std::uint64_t>(::syscall(SYS_gettid)));
  FlightRecorder& recorder = flight_recorder();
  const std::size_t n = recorder.snapshot_into(report_events);
  const TraceCounts c = recorder.counts();
  out.str("\nflight recorder: last ").dec(n).str(" events of ").dec(c.recorded);
  out.str(" (dropped ").dec(c.dropped).str(", torn ").dec(c.torn).str(")\n");
  out.str("t_ns ring seq code a b\n");
  for (std::size_t i = 0; i < n; ++i) {
    const TraceEvent& e = report_events[i];
    out.dec(e.t_ns).str(" ").dec(e.ring).str(" ").dec(e.seq).str(" ").str(to_string(e.code));
    out.str(" ").dec(e.a).str(" ").dec(e.b).str("\n");
  }
  out.str("end of report\n");
}
// [/snippet:report]

Expected<void, std::error_code> install_crash_report(int fd, std::string_view version) noexcept {
  load_build_id();
  report_fd = fd;
  version_size = std::min(version.size(), version_text.size() - 1);
  std::memcpy(version_text.data(), version.data(), version_size);

  stack_t ss{};
  ss.ss_sp = alt_stack.data();
  ss.ss_size = alt_stack.size();
  if (::sigaltstack(&ss, nullptr) != 0) {
    return Unexpected{std::error_code{errno, std::generic_category()}};
  }
  struct sigaction sa{};
  sa.sa_sigaction = on_fatal_signal;
  sa.sa_flags = static_cast<int>(SA_SIGINFO | SA_ONSTACK | SA_RESETHAND);  // glibc: unsigned constants
  sigemptyset(&sa.sa_mask);
  for (const int sig : fatal_signals) {
    if (::sigaction(sig, &sa, nullptr) != 0) {
      return Unexpected{std::error_code{errno, std::generic_category()}};
    }
  }
  return {};
}

}  // namespace minidaq::rt
