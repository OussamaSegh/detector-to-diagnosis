minidaq_mutation_exercise(e1_unwrap_tests MUTANTS 7 MIN_TESTS 15)
minidaq_mutation_exercise(e2_sorter_properties MUTANTS 8)
minidaq_exercise(e4_fault_injection LIBS minidaq::control)

# Exercise 18.3 measures coverage, so it exists only in a build with Clang's source-based coverage
# (the coverage preset); tools/release_checks.sh runs its solution and starter there.
if(CMAKE_CXX_FLAGS MATCHES "-fcoverage-mapping")
  find_package(Python3 REQUIRED COMPONENTS Interpreter)
  set(_e3 ${CMAKE_CURRENT_SOURCE_DIR}/e3_branch_coverage)
  set(_e3_variants)
  if(MINIDAQ_BUILD_EXERCISES)
    list(APPEND _e3_variants solution)
  endif()
  if(MINIDAQ_BUILD_STARTERS)
    list(APPEND _e3_variants starter)
  endif()
  foreach(_v IN LISTS _e3_variants)
    set(_t ch18_e3_branch_coverage_${_v})
    add_executable(${_t} ${_e3}/${_v}/test_sinogram_branches.cpp)
    target_link_libraries(${_t} PRIVATE minidaq::core GTest::gtest_main
      $<IF:$<STREQUAL:${_v},starter>,minidaq::warnings_no_error,minidaq::warnings>)
    add_test(NAME ch18/e3_branch_coverage/${_v}/coverage
      COMMAND ${Python3_EXECUTABLE} ${_e3}/tests/check_coverage.py --exe $<TARGET_FILE:${_t}>
              --source ${PROJECT_SOURCE_DIR}/minidaq/src/processing/sinogram.cpp
              --review ${_e3}/${_v}/review.json --min 90 --work ${CMAKE_CURRENT_BINARY_DIR}/${_t}.profiles)
    set_tests_properties(ch18/e3_branch_coverage/${_v}/coverage PROPERTIES LABELS ${_v} TIMEOUT 120)
  endforeach()
endif()

# Exercise 18.5: the variant's tests run with MiniDAQ's own tracker tests under
# tools/mutation_test.py; the check reads the variant's recorded report (see its README).
minidaq_exercise(e5_kill_survivors)
find_package(Python3 COMPONENTS Interpreter)
foreach(_v solution starter)
  if(TARGET ch18_e5_kill_survivors_${_v} AND Python3_Interpreter_FOUND)
    set(_e5 ${CMAKE_CURRENT_SOURCE_DIR}/e5_kill_survivors)
    add_test(NAME ch18/e5_kill_survivors/${_v}/survivors
      COMMAND ${Python3_EXECUTABLE} ${_e5}/tests/check_survivors.py ${_e5}/${_v}/mutation-report.txt
              ${_e5}/${_v}/survivors.json --source minidaq/include/minidaq/format/readout_packet.hpp
      WORKING_DIRECTORY ${PROJECT_SOURCE_DIR})
    set_tests_properties(ch18/e5_kill_survivors/${_v}/survivors PROPERTIES LABELS ${_v})
  endif()
endforeach()
