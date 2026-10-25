# Reproducible builds (Chapter 20). Selected by MINIDAQ_REPRODUCIBLE (preset `hardened`, the
# build that ships): the same commit, compiler and flags give the same bytes, whatever the
# directory the sources were checked out to.
#
# A release build without debug information is already path-independent. Debug information is
# not: it records the compilation directory and the absolute path of every source file, so two
# checkouts give two different programs. The maps below rewrite those paths to relative ones in
# the debug information and in __FILE__. A debugger then finds the sources when it is started
# from the top of a checkout of the same commit (Chapter 21). tools/repro_check.sh checks the
# result by building twice in two directories.
if(MINIDAQ_REPRODUCIBLE)
  if(NOT CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    message(FATAL_ERROR "MINIDAQ_REPRODUCIBLE supports GCC and Clang")
  endif()
  message(STATUS "MiniDAQ: reproducible paths enabled")
  # [snippet:maps]
  # The build directory may be inside the source directory, so both maps can match a generated
  # file. GCC 13 then uses the last map and Clang 18 the longest prefix: with the build
  # directory's map second, both choose it.
  add_compile_options(
    "-ffile-prefix-map=${CMAKE_SOURCE_DIR}/="
    "-ffile-prefix-map=${CMAKE_BINARY_DIR}/=build/")
  # [/snippet:maps]
endif()
