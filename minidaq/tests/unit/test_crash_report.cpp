// SPDX-License-Identifier: MIT
#include <fcntl.h>
#include <gtest/gtest.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <unistd.h>

#include <cerrno>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <thread>

#include "minidaq/core/flight_recorder.hpp"
#include "minidaq/rt/crash_report.hpp"

using namespace minidaq;

namespace {

std::string read_file(const std::filesystem::path& p) {
  std::ifstream f{p};
  std::stringstream s;
  s << f.rdbuf();
  return s.str();
}

// In the working directory (the build directory under ctest), and without the process ID: the
// child of a "threadsafe" death test is a new process that must find the same name.
std::filesystem::path report_path(const char* name) {
  return std::filesystem::current_path() / (std::string{"crash-report-test-"} + name + ".txt");
}

// In the child of a death test: no core file for a crash we cause on purpose, the handler
// installed, an event to find in the report.
void prepare_child(const std::filesystem::path& path) {
  const rlimit no_core{0, 0};
  (void)::setrlimit(RLIMIT_CORE, &no_core);
  const int fd = ::open(path.c_str(), O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
  if (fd < 0 || !rt::install_crash_report(fd, "test-1.2.3")) {
    std::_Exit(3);
  }
  trace(TraceCode::note, 42, 43);
}

}  // namespace

TEST(CrashReport, TheBuildIdIsTheOneTheLinkerWrote) {
  // REQ: SRS-DIAG-002
  const std::string_view id = rt::build_id();
  ASSERT_FALSE(id.empty()) << "linked without --build-id?";
  EXPECT_EQ(id.find_first_not_of("0123456789abcdef"), std::string_view::npos);
  // The same ID as readelf reads from the file, where binutils is installed.
  const std::string cmd = "readelf -n /proc/" + std::to_string(::getpid()) + "/exe 2>/dev/null";
  FILE* p = ::popen(cmd.c_str(), "r");
  ASSERT_NE(p, nullptr);
  std::string text;
  std::array<char, 256> buf{};
  while (std::fgets(buf.data(), static_cast<int>(buf.size()), p) != nullptr) {
    text += buf.data();
  }
  if (::pclose(p) != 0 || text.find("Build ID: ") == std::string::npos) {
    GTEST_SKIP() << "readelf not available";
  }
  EXPECT_NE(text.find("Build ID: " + std::string{id}), std::string::npos) << text;
}

TEST(CrashReport, AReportNamesTheSignalTheProgramAndTheLastEvents) {
  // REQ: SRS-DIAG-002
  const auto path = report_path("format");
  const int fd = ::open(path.c_str(), O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
  ASSERT_GE(fd, 0);
  std::thread{[] { trace(TraceCode::run_begin, 7, 0); }}.join();
  siginfo_t info{};
  info.si_signo = SIGSEGV;
  info.si_code = SEGV_MAPERR;
  info.si_addr = reinterpret_cast<void*>(0x10);  // NOLINT(performance-no-int-to-ptr)
  rt::write_crash_report(fd, SIGSEGV, &info);
  ::close(fd);
  const std::string report = read_file(path);
  std::filesystem::remove(path);
  EXPECT_EQ(report.rfind("MiniDAQ crash report\n", 0), 0U) << report;
  EXPECT_NE(report.find("signal: SIGSEGV (11) code 1 address 0x10\n"), std::string::npos) << report;
  EXPECT_NE(report.find("build-id: " + std::string{rt::build_id()} + "\n"), std::string::npos);
  EXPECT_NE(report.find(" run_begin 7 0\n"), std::string::npos) << report;
  EXPECT_NE(report.find("\nend of report\n"), std::string::npos);
}

TEST(CrashReport, ASignalSentByAnotherProcessNamesTheSenderInsteadOfAnAddress) {
  // REQ: SRS-DIAG-002
  const auto path = report_path("sent");
  const int fd = ::open(path.c_str(), O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
  ASSERT_GE(fd, 0);
  siginfo_t info{};
  info.si_signo = SIGSEGV;
  info.si_code = SI_USER;  // kill(1): the fields of a fault are not set, si_pid is
  info.si_pid = 4321;
  rt::write_crash_report(fd, SIGSEGV, &info);
  ::close(fd);
  const std::string report = read_file(path);
  std::filesystem::remove(path);
  EXPECT_NE(report.find("signal: SIGSEGV (11) sent by pid 4321\n"), std::string::npos) << report;
}

TEST(CrashReport, NamesTheFatalSignals) {
  EXPECT_EQ(rt::signal_name(SIGSEGV), "SIGSEGV");
  EXPECT_EQ(rt::signal_name(SIGBUS), "SIGBUS");
  EXPECT_EQ(rt::signal_name(SIGFPE), "SIGFPE");
  EXPECT_EQ(rt::signal_name(SIGILL), "SIGILL");
  EXPECT_EQ(rt::signal_name(SIGABRT), "SIGABRT");
  EXPECT_EQ(rt::signal_name(SIGTERM), "signal");
}

// The death tests crash a child process on purpose. Sanitizers install their own handlers for
// these signals and report the crash themselves, so the tests do not run under them.
#if defined(MINIDAQ_SANITIZED)
#define MINIDAQ_SKIP_UNDER_SANITIZERS() GTEST_SKIP() << "sanitizers handle fatal signals themselves"
#else
#define MINIDAQ_SKIP_UNDER_SANITIZERS() (void)0
#endif

TEST(CrashReportDeathTest, AFaultWritesTheReportAndTheProcessStillDiesOfIt) {
  // REQ: SRS-DIAG-002
  MINIDAQ_SKIP_UNDER_SANITIZERS();
  GTEST_FLAG_SET(death_test_style, "threadsafe");
  const auto path = report_path("segv");
  EXPECT_EXIT(
      {
        prepare_child(path);
        // A page we may not touch: a real fault, without undefined behavior in the program.
        void* page = ::mmap(nullptr, 4096, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        *static_cast<volatile int*>(page) = 1;
      },
      testing::KilledBySignal(SIGSEGV), "");
  const std::string report = read_file(path);
  std::filesystem::remove(path);
  EXPECT_NE(report.find("signal: SIGSEGV (11) code 2 address 0x"), std::string::npos) << report;
  EXPECT_NE(report.find("version: test-1.2.3\n"), std::string::npos) << report;
  EXPECT_NE(report.find(" note 42 43\n"), std::string::npos) << report;
  EXPECT_NE(report.find("\nend of report\n"), std::string::npos) << report;
}

TEST(CrashReportDeathTest, AnAbortWritesTheReportAndTheProcessStillDiesOfIt) {
  // REQ: SRS-DIAG-002
  MINIDAQ_SKIP_UNDER_SANITIZERS();
  GTEST_FLAG_SET(death_test_style, "threadsafe");
  const auto path = report_path("abort");
  EXPECT_EXIT(
      {
        prepare_child(path);
        std::abort();
      },
      testing::KilledBySignal(SIGABRT), "");
  const std::string report = read_file(path);
  std::filesystem::remove(path);
  EXPECT_NE(report.find("signal: SIGABRT (6)"), std::string::npos) << report;
  EXPECT_NE(report.find(" note 42 43\n"), std::string::npos) << report;
}
