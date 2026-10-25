minidaq_python_exercise(e1_link_accounting)
minidaq_python_exercise(e2_golden_power)
minidaq_python_exercise(e3_soak_analysis)
minidaq_mutation_exercise(e4_batching_test MUTANTS 5)

# Exercise 19.5 records minidaq_send and replays into minidaq_server, so its tests need the
# programs, with the same time factor as the system tests under the sanitizers.
find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND AND TARGET minidaq_server)
  set(_time_factor 1)
  if(MINIDAQ_SANITIZERS)
    set(_time_factor 10)
  endif()
  set(_e5 ${CMAKE_CURRENT_SOURCE_DIR}/e5_udp_replay)
  set(_e5_variants)
  if(MINIDAQ_BUILD_EXERCISES)
    list(APPEND _e5_variants solution)
  endif()
  if(MINIDAQ_BUILD_STARTERS)
    list(APPEND _e5_variants starter)
  endif()
  foreach(_v IN LISTS _e5_variants)
    add_test(NAME ch19/e5_udp_replay/${_v}/unittest
             COMMAND ${Python3_EXECUTABLE} -m unittest discover -s ${_e5}/tests -t ${_e5}/tests)
    set_tests_properties(ch19/e5_udp_replay/${_v}/unittest PROPERTIES LABELS ${_v} TIMEOUT 600
      ENVIRONMENT "PYTHONPATH=${_e5}/${_v};PYTHONDONTWRITEBYTECODE=1;MINIDAQ_APPS=$<TARGET_FILE_DIR:minidaq_server>;MINIDAQ_TEST_TIME_FACTOR=${_time_factor}")
  endforeach()
endif()
