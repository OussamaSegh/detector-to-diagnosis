minidaq_python_exercise(e1_trailers)
minidaq_python_exercise(e2_object_names)
minidaq_python_exercise(e3_merge3)
minidaq_python_exercise(e4_bisect)

# Exercise 36.5 (A): an audit. Your tests (starter/ or solution/) run against the corrected
# change, the agent's change and each of its defects; tools/audit_exercises.py checks its record.
minidaq_python_exercise(audit-push-guard)
find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
  add_test(NAME ch36/audit-push-guard/record
           COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/audit_exercises.py ${PROJECT_SOURCE_DIR}
                   exercises/ch36/audit-push-guard)
  set_tests_properties(ch36/audit-push-guard/record PROPERTIES LABELS unit)
endif()
