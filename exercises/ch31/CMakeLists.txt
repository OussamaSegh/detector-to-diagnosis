minidaq_python_exercise(e1_pair_counts)
minidaq_python_exercise(e2_timing_fit)
minidaq_pybind_exercise(e3_histogram MODULE dthist)
minidaq_python_exercise(e4_running_stats)

# Exercise 31.5 (A): an audit. Your tests (starter/ or solution/) run against the corrected
# change, the agent's change and each of its defects; tools/audit_exercises.py checks its record.
minidaq_python_exercise(audit-output-array)
find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
  add_test(NAME ch31/audit-output-array/record
           COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/audit_exercises.py ${PROJECT_SOURCE_DIR}
                   exercises/ch31/audit-output-array)
  set_tests_properties(ch31/audit-output-array/record PROPERTIES LABELS unit)
endif()
