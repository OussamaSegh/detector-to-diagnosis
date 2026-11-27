minidaq_python_exercise(e1_review)
minidaq_exercise(e2_postmortem)
minidaq_exercise(e3_flight_recorder)
minidaq_python_exercise(e4_incident_data)
minidaq_python_exercise(e5_bisect)

# Exercise 21.6 (A): an audit. Your tests (starter/ or solution/) run against the corrected
# change, the agent's change and each of its defects; tools/audit_exercises.py checks its record.
minidaq_python_exercise(audit-version-check)
find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
  add_test(NAME ch21/audit-version-check/record
           COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/audit_exercises.py ${PROJECT_SOURCE_DIR}
                   exercises/ch21/audit-version-check)
  set_tests_properties(ch21/audit-version-check/record PROPERTIES LABELS unit)
endif()
