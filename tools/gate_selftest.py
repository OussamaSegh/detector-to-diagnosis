#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Shows that each gate of MiniDAQ's pipeline can fail (Chapter 20).

A gate that has never failed proves nothing: a static analyzer that reads no files, a trace
check that compares a file with itself and a sanitizer that is not linked in all report success.
This tool plants one known fault at a time in a fresh checkout of a commit, runs the gate that
should catch it, and records whether the gate failed, and failed for the planted reason (its
output matches what the fault must produce). It also runs each gate on the unchanged checkout
first: a gate that fails on correct code would "catch" every fault.

    gate_selftest.py OUT.md [--commit REF] [--only ID,ID] [--keep]

Writes a Markdown report to OUT.md (with the gates' output in OUT.log). Exit status 0 only if
every gate passes on the unchanged code and catches its fault for the planted reason.
"""
import argparse
import dataclasses
import datetime
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEBUG = "build/debug"  # in the checkout
TIDY = "build/clang-release"


@dataclasses.dataclass
class Fault:
    id: str
    gate: str  # what the gate is, in the words of the report
    planted: str  # what the fault is
    edits: list  # (path, old, new): old must occur exactly once in path
    command: list  # the gate, run from the top of the checkout
    expect: str  # regular expression the gate's output must match when it catches the fault
    files: dict = dataclasses.field(default_factory=dict)  # extra files to write: path -> text


CRC = "minidaq/src/core/crc32.cpp"
CRC_ANON = "std::uint32_t byte_at(std::span<const std::byte> d, std::size_t i) noexcept {"
PROGRAM_OK = '#include <cstdio>\nint main() { std::puts("ok"); }\n'

# [snippet:faults]
FAULTS = [
    Fault("warning", "build: warnings are errors", "an unused function in a library source",
          [(CRC, CRC_ANON, "std::uint32_t unused_helper() noexcept { return 0; }\n\n" + CRC_ANON)],
          ["cmake", "--build", DEBUG, "--target", "minidaq_core"], r"unused-function"),
    Fault("unit", "unit tests", "the slicing-by-8 CRC reads byte 6 twice instead of bytes 6 and 7",
          [(CRC, "t[0][byte_at(data, i + 7)]", "t[0][byte_at(data, i + 6)]")],
          ["sh", "-c", f"cmake --build {DEBUG} --target minidaq_unit_tests >/dev/null && "
                       f"ctest --test-dir {DEBUG} -R '^Crc32[.]' --output-on-failure"],
          r"Crc32\.SlicingBy8MatchesTheBytewiseLoop\w* \.+\*+Failed"),
    Fault("system", "system tests", "the client exits with 0 when the server refuses its token",
          [("minidaq/apps/minidaq_ctl.cpp", '      return 1;\n    }\n  }\n  if (cmd == "wait")',
            '      return 0;\n    }\n  }\n  if (cmd == "wait")')],
          ["sh", "-c", f"cmake --build {DEBUG} --target minidaq_ctl minidaq_server >/dev/null && "
                       f"ctest --test-dir {DEBUG} -R '^system[.]control$' --output-on-failure"],
          r"system\.control \.+\*+Failed"),
    Fault("tidy", "static analysis: clang-tidy", "a pointer initialized with 0",
          [(CRC, CRC_ANON, "[[maybe_unused]] const std::uint32_t* const kNoTable = 0;\n\n" + CRC_ANON)],
          ["tools/static_analysis.sh", TIDY], r"modernize-use-nullptr"),
    Fault("cppcheck", "static analysis: cppcheck", "an array read one past its end",
          [(CRC, CRC_ANON, "[[maybe_unused]] int past_the_end() { const int a[2] = {0, 0}; return a[2]; }\n\n"
            + CRC_ANON)],
          ["tools/static_analysis.sh", TIDY], r"arrayIndexOutOfBounds"),
    Fault("layers", "architecture: layers", "the core includes the application layer",
          [(CRC, '#include "minidaq/core/crc32.hpp"',
            '#include "minidaq/core/crc32.hpp"\n#include "minidaq/control/acquisition_service.hpp"')],
          ["python3", "tools/check_layers.py", "."], r"core may not include application"),
    Fault("trace", "trace matrix", "a test loses the tag of the only requirement it verifies",
          # The tag is spelled in two pieces, or the trace matrix would count this file as its test.
          [("minidaq/tests/unit/test_config.cpp", "  // REQ" + ": SRS-CFG-001\n", "\n")],
          ["python3", "tools/trace_matrix.py", ".", "--check"], r"SRS-CFG-001: verified by test, but no test names it"),
    Fault("srs", "requirements in testable form", "a requirement that cannot be verified",
          [("docs/regulatory/srs.md", "| SRS-SRT-001 |", "| SRS-SRT-999 | The sorter shall be fast. | sorter | T |\n| SRS-SRT-001 |")],
          ["python3", "tools/req_lint.py", "docs/regulatory/srs.md"], r"SRS-SRT-999: vague word 'fast'"),
    Fault("soup", "SOUP list", "a dependency pin changed without the SOUP list",
          [("cmake/Dependencies.cmake", "b514bdc898e2951020cbdca1304b75f5950d1f59", "0" * 40)],
          ["python3", "tools/check_soup.py", "."], r"googletest: pin 0{40} is not in the SOUP list"),
    Fault("document", "document control", "a controlled document changed without a new version",
          [("docs/regulatory/verification/stp.md", "This plan says how", "This plan, changed, says how")],
          ["python3", "tools/design_file.py", ".", "--check", "--since", "HEAD"],
          r"stp\.md: changed since HEAD but still version"),
    Fault("waits", "test waits (CAPA-0001)", "a test that sleeps without a reason",
          [("minidaq/tests/unit/test_config.cpp", "TEST(Config, MinimalDocumentGetsDefaults) {",
            "TEST(Config, Sleeps) { std::this_thread::sleep_for(std::chrono::milliseconds(10)); }\n\n"
            "TEST(Config, MinimalDocumentGetsDefaults) {")],
          ["python3", "tools/check_test_waits.py", "."], r"a sleep without"),
    Fault("hardening", "hardening of the shipped programs", "a program linked without PIE and BIND_NOW",
          [], ["sh", "-c", "g++ -O2 -no-pie -Wl,-z,lazy selftest/p.cpp -o selftest/p && "
                           "python3 tools/check_hardening.py selftest/p"],
          r"pie=no .*bind_now=no", {"selftest/p.cpp": PROGRAM_OK}),
    Fault("perf", "performance regression gate", "the pipeline benchmark 20% slower",
          [], ["sh", "-c", "python3 selftest/slow.py && python3 tools/perf_gate.py benchmarks/baseline/book-vm.json "
                           "selftest/slow.json --strict"],
          r"BM_Pipeline/4096/64/real_time .*REGRESSION",
          {"selftest/slow.py": "import json\nd = json.load(open('benchmarks/baseline/book-vm.json'))\n"
                               "for b in d['benchmarks']:\n"
                               "    if b.get('run_name', b['name']).startswith('BM_Pipeline') and 'items_per_second' in b:\n"
                               "        b['items_per_second'] *= 0.8\n"
                               "json.dump(d, open('selftest/slow.json', 'w'))\n"}),
    Fault("asan", "AddressSanitizer", "a heap read one past the end",
          [], ["sh", "-c", "clang++-18 -g -fsanitize=address selftest/p.cpp -o selftest/p && selftest/p"],
          r"heap-buffer-overflow",
          {"selftest/p.cpp": "#include <vector>\nint main() { std::vector<int> v(4); return v.data()[4]; }\n"}),
    Fault("tsan", "ThreadSanitizer", "two threads increment one int",
          [], ["sh", "-c", "clang++-18 -g -O1 -fsanitize=thread selftest/p.cpp -o selftest/p && selftest/p"],
          r"data race",
          {"selftest/p.cpp": "#include <thread>\nint n = 0;\nint main() { std::thread a([] { ++n; }), b([] { ++n; });"
                             " a.join(); b.join(); return n == 3; }\n"}),
]
# [/snippet:faults]


def sh(cmd, cwd, log):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    out = p.stdout + p.stderr
    log.write(f"$ {' '.join(cmd)}\n{out}\nexit {p.returncode}\n\n")
    return p.returncode, out


def plant(top, fault):
    for path, old, new in fault.edits:
        f = top / path
        text = f.read_text()
        if text.count(old) != 1:
            raise RuntimeError(f"fault {fault.id}: {path} has {text.count(old)} occurrences of the text to replace")
        f.write_text(text.replace(old, new))
    for path, text in fault.files.items():
        (top / path).parent.mkdir(parents=True, exist_ok=True)
        (top / path).write_text(text)


def control_files(fault):
    """For a gate that runs on generated input, the correct input of the positive control."""
    if fault.id == "hardening":
        return {"selftest/p.cpp": PROGRAM_OK}, ["sh", "-c", "g++ -O2 -fPIE -pie -fcf-protection=full "
                                                "-Wl,-z,relro,-z,now,-z,noexecstack selftest/p.cpp -o selftest/p && "
                                                "python3 tools/check_hardening.py selftest/p"]
    if fault.id == "perf":
        return {}, ["python3", "tools/perf_gate.py", "benchmarks/baseline/book-vm.json",
                    "benchmarks/baseline/book-vm.json", "--strict"]
    if fault.id in ("asan", "tsan"):
        flags = "-fsanitize=address" if fault.id == "asan" else "-O1 -fsanitize=thread"
        text = ("#include <thread>\n#include <atomic>\nstd::atomic<int> n{0};\nint main() { std::thread a([] { ++n; }), "
                "b([] { ++n; }); a.join(); b.join(); return n == 2 ? 0 : 1; }\n")
        return {"selftest/p.cpp": text}, ["sh", "-c", f"clang++-18 -g {flags} selftest/p.cpp -o selftest/p && selftest/p"]
    return {}, fault.command


# [snippet:verdict]
def verdict(clean_status, status, out, expect):
    """What one run of a gate shows: on the unchanged code (clean_status) and with the fault."""
    if clean_status != 0:
        return "gate fails on correct code"
    if status == 0:
        return "NOT CAUGHT"
    if re.search(expect, out) is None:
        return "failed for another reason"
    return "caught"
# [/snippet:verdict]


def restore(top):
    subprocess.run(["git", "checkout", "--quiet", "--", "."], cwd=top, check=True)
    shutil.rmtree(top / "selftest", ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=pathlib.Path)
    ap.add_argument("--commit", default="HEAD")
    ap.add_argument("--only", help="comma-separated fault IDs")
    ap.add_argument("--keep", action="store_true", help="keep the checkout")
    args = ap.parse_args(argv)
    faults = [f for f in FAULTS if not args.only or f.id in args.only.split(",")]
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", args.commit], capture_output=True, text=True,
                            check=True).stdout.strip()
    work = pathlib.Path(tempfile.mkdtemp(prefix="gate-selftest-"))
    top = work / "checkout"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows, ok = [], True
    started = datetime.datetime.now(datetime.timezone.utc)
    with open(args.out.with_suffix(".log"), "w") as log:
        subprocess.run(["git", "-C", str(ROOT), "worktree", "add", "--quiet", "--detach", str(top), commit], check=True)
        try:
            needs_build = {"warning", "unit", "system"} & {f.id for f in faults}
            needs_tidy = {"tidy", "cppcheck"} & {f.id for f in faults}
            setup = []
            if needs_build:
                setup += [["cmake", "--preset", "debug", "-DMINIDAQ_BUILD_EXERCISES=OFF", "-DMINIDAQ_BUILD_BENCHMARKS=OFF"],
                          ["cmake", "--build", DEBUG]]
            if needs_tidy:
                setup += [["cmake", "--preset", "clang-release", "-DMINIDAQ_BUILD_EXERCISES=OFF",
                           "-DMINIDAQ_BUILD_BENCHMARKS=OFF"]]
            for cmd in setup:
                status, out = sh(cmd, top, log)
                if status != 0:
                    print(out[-3000:], file=sys.stderr)
                    sys.exit(f"setup failed: {' '.join(cmd)}")
            for fault in faults:
                # [snippet:run]
                files, control = control_files(fault)
                for path, text in files.items():
                    (top / path).parent.mkdir(parents=True, exist_ok=True)
                    (top / path).write_text(text)
                clean_status, _ = sh(control, top, log)
                restore(top)
                plant(top, fault)
                status, out = sh(fault.command, top, log)
                restore(top)
                result = verdict(clean_status, status, out, fault.expect)
                # [/snippet:run]
                ok &= result == "caught"
                rows.append((fault, clean_status, status, result))
                print(f"{result:28} {fault.id:10} {fault.gate}")
            if needs_build:  # the planted faults were rebuilt; leave the build as the commit is
                sh(["cmake", "--build", DEBUG], top, log)
        finally:
            if not args.keep:
                subprocess.run(["git", "-C", str(ROOT), "worktree", "remove", "--force", str(top)], check=False)
                shutil.rmtree(work, ignore_errors=True)

    lines = ["# MiniDAQ gate self-test", "",
             f"Commit `{commit[:12]}`, {started:%Y-%m-%d %H:%M} UTC, written by `tools/gate_selftest.py`. Each gate",
             "ran on the unchanged checkout (control) and then with one planted fault.", "",
             "| Fault | Gate | Planted | Control | With the fault | Verdict |", "|---|---|---|---|---|---|"]
    for fault, clean_status, status, result in rows:
        lines.append(f"| `{fault.id}` | {fault.gate} | {fault.planted} | "
                     f"{'pass' if clean_status == 0 else 'FAIL'} | {'fail' if status else 'pass'} | {result} |")
    lines += ["", f"{sum(r[3] == 'caught' for r in rows)} of {len(rows)} faults caught for the planted reason.", ""]
    args.out.write_text("\n".join(lines))
    print(f"{args.out}: {sum(r[3] == 'caught' for r in rows)} of {len(rows)} caught")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
