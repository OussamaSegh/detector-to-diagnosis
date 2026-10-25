minidaq_python_exercise(e1_manifest)
minidaq_python_exercise(e3_gate_selftest)
minidaq_python_exercise(e4_ab_drift)
minidaq_python_exercise(e5_flaky_triage)

# Exercise 20.2 builds a small CMake project twice and compares the programs, so its test needs
# CMake, Ninja and the compiler of this build.
find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
  set(_e2 ${CMAKE_CURRENT_SOURCE_DIR}/e2_reproducible)
  set(_e2_variants)
  if(MINIDAQ_BUILD_EXERCISES)
    list(APPEND _e2_variants solution)
  endif()
  if(MINIDAQ_BUILD_STARTERS)
    list(APPEND _e2_variants starter)
  endif()
  foreach(_v IN LISTS _e2_variants)
    add_test(NAME ch20/e2_reproducible/${_v}/unittest
             COMMAND ${Python3_EXECUTABLE} ${_e2}/tests/test_reproducible.py ${_e2}/${_v} ${CMAKE_CXX_COMPILER})
    set_tests_properties(ch20/e2_reproducible/${_v}/unittest PROPERTIES LABELS ${_v} TIMEOUT 300
      ENVIRONMENT "PYTHONDONTWRITEBYTECODE=1")
  endforeach()
endif()
