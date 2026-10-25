# Third-party dependencies (SOUP, see docs/regulatory/soup-list.md).
# Default: pinned by exact git commit through FetchContent, so every build of a
# given MiniDAQ version uses byte-identical sources. MINIDAQ_USE_SYSTEM_DEPS=ON
# uses distribution packages instead (offline builds); record their versions
# in the release notes if you ship such a build.
include(FetchContent)

if(MINIDAQ_BUILD_TESTS OR MINIDAQ_BUILD_EXERCISES OR MINIDAQ_BUILD_STARTERS)
  if(MINIDAQ_USE_SYSTEM_DEPS)
    find_package(GTest 1.14 REQUIRED)
  else()
    set(INSTALL_GTEST OFF CACHE BOOL "" FORCE)
    set(BUILD_GMOCK ON CACHE BOOL "" FORCE)
    FetchContent_Declare(googletest
      GIT_REPOSITORY https://github.com/google/googletest.git
      GIT_TAG        b514bdc898e2951020cbdca1304b75f5950d1f59 # v1.15.2
      GIT_SHALLOW    FALSE
      SYSTEM)
    FetchContent_MakeAvailable(googletest)
  endif()
endif()

if(MINIDAQ_BUILD_BENCHMARKS)
  if(MINIDAQ_USE_SYSTEM_DEPS)
    find_package(benchmark 1.8 REQUIRED)
  else()
    set(BENCHMARK_ENABLE_TESTING OFF CACHE BOOL "" FORCE)
    set(BENCHMARK_ENABLE_INSTALL OFF CACHE BOOL "" FORCE)
    set(BENCHMARK_ENABLE_WERROR OFF CACHE BOOL "" FORCE)
    FetchContent_Declare(googlebenchmark
      GIT_REPOSITORY https://github.com/google/benchmark.git
      GIT_TAG        96afad55c79e02f5dfca1374e772c2be72ba631b # v1.9.1
      SYSTEM)
    FetchContent_MakeAvailable(googlebenchmark)
  endif()
endif()

# JSON for the control plane (configuration files, control API, audit trail).
# Never used on the hot path. Decision record: docs/adr/0004-json-library.md.
if(MINIDAQ_USE_SYSTEM_DEPS)
  find_package(nlohmann_json 3.12 REQUIRED)  # 3.11 has MDQ-PR-005 (CR-0002)
else()
  FetchContent_Declare(nlohmann_json
    URL      https://github.com/nlohmann/json/releases/download/v3.12.0/json.tar.xz
    URL_HASH SHA256=42f6e95cad6ec532fd372391373363b62a14af6d771056dbfc86160e6dfff7aa
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE
    SYSTEM)
  FetchContent_MakeAvailable(nlohmann_json)
endif()
