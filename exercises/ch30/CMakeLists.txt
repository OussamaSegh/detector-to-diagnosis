minidaq_python_exercise(e1_width)
minidaq_python_exercise(e2_regions)
minidaq_python_exercise(e3_qc)
minidaq_python_exercise(e4_uniformity)

# Exercise 30.5 (A): an audit. Your tests (starter/ or solution/) run against the corrected
# change, the agent's change and each of its defects; tools/audit_exercises.py checks its record.
minidaq_python_exercise(audit-qc-metadata)
find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
  add_test(NAME ch30/audit-qc-metadata/record
           COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/audit_exercises.py ${PROJECT_SOURCE_DIR}
                   exercises/ch30/audit-qc-metadata)
  set_tests_properties(ch30/audit-qc-metadata/record PROPERTIES LABELS unit)
endif()
