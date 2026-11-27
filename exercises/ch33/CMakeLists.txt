minidaq_exercise(e1_counts_add_up)
minidaq_python_exercise(e2_acceptance_verdict)
minidaq_python_exercise(e3_requirements_freeze)
minidaq_python_exercise(e4_soak_verdict)

# Exercise 33.5 (A): an audit. Your tests (starter/ or solution/) run against the corrected
# change, the agent's change and each of its defects; tools/audit_exercises.py checks its record.
minidaq_python_exercise(audit-run-counts)
find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
  add_test(NAME ch33/audit-run-counts/record
           COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/audit_exercises.py ${PROJECT_SOURCE_DIR}
                   exercises/ch33/audit-run-counts)
  set_tests_properties(ch33/audit-run-counts/record PROPERTIES LABELS unit)
endif()
