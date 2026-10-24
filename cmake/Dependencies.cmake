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
