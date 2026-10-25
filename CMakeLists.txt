cmake_minimum_required(VERSION 3.28)

file(READ "${CMAKE_CURRENT_SOURCE_DIR}/VERSION" MINIDAQ_VERSION_FILE)
string(STRIP "${MINIDAQ_VERSION_FILE}" MINIDAQ_VERSION_FULL)
# VERSION may carry a pre-release suffix (0.2.0-dev); CMake wants only X.Y.Z.
string(REGEX MATCH "^[0-9]+\\.[0-9]+\\.[0-9]+" MINIDAQ_VERSION "${MINIDAQ_VERSION_FULL}")

project(minidaq
  VERSION ${MINIDAQ_VERSION}
  DESCRIPTION "MiniDAQ: a simulated PET data acquisition chain (companion code for The NeuroLF Engineer)"
  LANGUAGES CXX)

if(PROJECT_IS_TOP_LEVEL)
  set(CMAKE_CXX_STANDARD 20 CACHE STRING "C++ standard (20 or 23)")
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
  set(CMAKE_CXX_EXTENSIONS OFF)
  set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
# MiniDAQ uses no C++20 modules. Newer CMake versions scan for them with Clang
# and put @file.modmap arguments into compile_commands.json, which clang-tidy
# cannot read (seen with the CMake on GitHub's ubuntu-24.04 runner).
set(CMAKE_CXX_SCAN_FOR_MODULES OFF)
endif()

option(MINIDAQ_WARNINGS_AS_ERRORS "Treat compiler warnings as errors" ON)
option(MINIDAQ_BUILD_TESTS "Build unit and component tests" ON)
option(MINIDAQ_BUILD_BENCHMARKS "Build Google Benchmark micro-benchmarks" ON)
option(MINIDAQ_BUILD_EXERCISES "Build exercise solutions (and their tests)" ON)
option(MINIDAQ_BUILD_STARTERS "Build exercise starters (their tests fail until you solve them)" OFF)
option(MINIDAQ_USE_SYSTEM_DEPS "Use system packages for GoogleTest/Benchmark/json instead of pinned FetchContent" OFF)
set(MINIDAQ_SANITIZERS "" CACHE STRING "Semicolon list of sanitizers: address;undefined | thread")
option(MINIDAQ_BUILD_FUZZERS "Build libFuzzer targets (Clang only; instruments all code for coverage)" OFF)
option(MINIDAQ_HARDENING "Compiler and linker hardening for shipped builds (ADR 0008)" OFF)
option(MINIDAQ_REPRODUCIBLE "Path-independent debug information and __FILE__ for shipped builds (Chapter 20)" OFF)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
include(Warnings)
include(Sanitizers)
include(Hardening)
include(Reproducible)
include(Dependencies)

if(MINIDAQ_BUILD_TESTS)
  enable_testing()
  include(GoogleTest)
endif()

add_subdirectory(minidaq)

if(MINIDAQ_BUILD_BENCHMARKS)
  add_subdirectory(benchmarks)
endif()

if(MINIDAQ_BUILD_FUZZERS)
  add_subdirectory(fuzz)
endif()

if(MINIDAQ_BUILD_EXERCISES OR MINIDAQ_BUILD_STARTERS)
  add_subdirectory(exercises)
endif()
