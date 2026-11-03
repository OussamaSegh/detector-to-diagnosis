# SPDX-License-Identifier: MIT
# The analysis package (Chapter 31): its tests, type check and lint as CTest tests. They skip
# (status 77) where the Python environment of analysis/requirements.lock is not installed; the
# CI job "python" installs it and runs them.
if(NOT MINIDAQ_BUILD_TESTS)
  return()
endif()
find_package(Python3 COMPONENTS Interpreter)
if(NOT Python3_Interpreter_FOUND)
  return()
endif()
add_test(NAME analysis.pytest COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/run_checks.py pytest)
add_test(NAME analysis.mypy COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/run_checks.py mypy)
add_test(NAME analysis.ruff COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/run_checks.py ruff)
set_tests_properties(analysis.pytest analysis.mypy analysis.ruff PROPERTIES
  LABELS "unit" SKIP_RETURN_CODE 77 TIMEOUT 600)
if(TARGET minidaq_sim)
  set_tests_properties(analysis.pytest PROPERTIES ENVIRONMENT "MINIDAQ_APPS=$<TARGET_FILE_DIR:minidaq_sim>")
endif()
