minidaq_python_exercise(e1_kind_of_release)
minidaq_python_exercise(e2_support_matrix)
minidaq_python_exercise(e3_affected_releases)
minidaq_python_exercise(e4_affected_version)

# Exercise 40.5 (A): an audit. Your tests (starter/ or solution/) run against the corrected
# change, the agent's change and each of its defects; tools/audit_exercises.py checks its record.
minidaq_python_exercise(audit-update-state)
find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
  add_test(NAME ch40/audit-update-state/record
           COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/audit_exercises.py ${PROJECT_SOURCE_DIR}
                   exercises/ch40/audit-update-state)
  set_tests_properties(ch40/audit-update-state/record PROPERTIES LABELS unit)
endif()
