#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 37 measurement: which test of Exercise 37.3 catches which version of the function.

    python3 measurements/ch37/mutants.py OUT_TEXT [CXX]

Compiles the starter's two tests and the solution's eight against tests/subject.hpp with
EX_MUTANT=0 to 7, and records, for each test and each version, whether the test fails. The
tests are compiled with a minimal stand-in for GoogleTest's TEST, EXPECT_TRUE and EXPECT_FALSE
(written to a temporary directory), so the measurement needs only a C++17 compiler; the exercise
itself runs on the real GoogleTest under CTest.
"""
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
EX = HERE.parent.parent / "exercises/ch37/e3_review_by_tests"
SHIM = r"""
#pragma once
#include <cstdio>
#include <vector>
struct ShimTest { const char* name; void (*fn)(bool&); };
inline std::vector<ShimTest>& shim_tests() { static std::vector<ShimTest> t; return t; }
struct ShimReg { ShimReg(const char* n, void (*f)(bool&)) { shim_tests().push_back({n, f}); } };
#define TEST(s, n) static void s##_##n(bool&); static ShimReg s##_##n##_reg(#n, s##_##n); \
  static void s##_##n(bool& shim_failed)
#define EXPECT_TRUE(c) do { if (!(c)) shim_failed = true; } while (0)
#define EXPECT_FALSE(c) do { if (c) shim_failed = true; } while (0)
int main() {
  for (auto& t : shim_tests()) { bool f = false; t.fn(f); std::printf("%s %d\n", t.name, f ? 1 : 0); }
}
"""
MUTANTS = ["as required", "< for <=", "wrap forgotten", "one way around", "inputs masked",
           "32-bit distance", "period off by one", "window unlimited"]


def run(cxx, tmp, src, mutant):
    exe = tmp / f"t{mutant}"
    subprocess.run([cxx, "-std=c++17", "-O1", f"-DEX_MUTANT={mutant}", f"-I{tmp}", f"-I{EX / 'tests'}",
                    "-include", str(tmp / "gtest/gtest.h"), "-o", str(exe), str(src)], check=True)
    out = subprocess.run([str(exe)], check=True, capture_output=True, text=True).stdout
    return [(n, f == "1") for n, f in (line.split() for line in out.splitlines())]


def main(out, cxx="c++"):
    lines = ["Chapter 37: which test of Exercise 37.3 catches which version of assisted::coincident",
             "1 = the test fails on that version (the mutant is caught); version 0 is the function as required",
             "versions: " + "; ".join(f"{i} {m}" for i, m in enumerate(MUTANTS)), ""]
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        (tmp / "gtest").mkdir()
        (tmp / "gtest/gtest.h").write_text(SHIM)
        for which in ("starter", "solution"):
            src = EX / which / "test_review.cpp"
            res = [dict(run(cxx, tmp, src, m)) for m in range(len(MUTANTS))]
            lines.append(f"{which} ({len(res[0])} tests)")
            for name in res[0]:
                lines.append(f"  {name:40s} " + " ".join(str(int(r[name])) for r in res))
            caught = sum(any(r.values()) for r in res[1:])
            lines.append(f"  mutants caught: {caught} of {len(MUTANTS) - 1}; version 0 passes: {not any(res[0].values())}")
            lines.append("")
    pathlib.Path(out).write_text("\n".join(lines))


if __name__ == "__main__":
    main(*sys.argv[1:])
