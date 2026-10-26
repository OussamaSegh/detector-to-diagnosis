// SPDX-License-Identifier: MIT
// MiniDAQ - the crash report: what a dying process writes about itself (Chapter 21).
//
// When the server dies of SIGSEGV, SIGBUS, SIGFPE, SIGILL or SIGABRT, the handler installed
// here writes a short text report to a file opened at start: the signal and its address, the
// version and the build ID of the program (to find its debug information later, Chapter 20),
// the process and thread, and the last events of the flight recorder. Then it gives the signal
// back to the kernel with its default action, so that the process still ends as it would have
// without the handler: killed by the signal, with a core dump where the system keeps them.
//
// A signal handler may call only async-signal-safe functions (POSIX lists them; write(2),
// clock_gettime and raise are among them, malloc, printf and std::string are not). Everything
// the handler needs is prepared by install_crash_report() before any crash: the file is open,
// the build ID is read, the alternate stack is allocated, the strings are formatted into static
// buffers by hand.
//
// The alternate stack (sigaltstack) is per thread: it serves the thread that called install.
// A stack overflow in another thread finds no stack to run the handler on; the kernel then
// kills the process with the default action, so there is a core dump but no report.
#pragma once

#include <csignal>
#include <span>
#include <string_view>
#include <system_error>

#include "minidaq/core/expected.hpp"

namespace minidaq::rt {

// Installs the handler for the fatal signals. The report goes to `fd` (the caller keeps it open
// for the life of the process; -1 disables the report but keeps the build ID). `version` is
// copied (at most 63 characters). Call once, early in main.
[[nodiscard]] Expected<void, std::error_code> install_crash_report(int fd, std::string_view version) noexcept;

// The GNU build ID of the program, in hex (empty if the linker wrote none). Read from the
// program's own ELF notes in memory.
[[nodiscard]] std::string_view build_id() noexcept;

// Writes a report as the handler does, for the given signal information (nullptr: none), to
// `fd`. Async-signal-safe. Exposed for tests and for the "diagnostics" command.
void write_crash_report(int fd, int sig, const siginfo_t* info) noexcept;

// The name of a signal ("SIGSEGV"), or "signal" for one this file does not name.
[[nodiscard]] std::string_view signal_name(int sig) noexcept;

}  // namespace minidaq::rt
