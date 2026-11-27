minidaq_python_exercise(e1_time_window)
minidaq_python_exercise(e2_energy_window)
minidaq_exercise(e3_randoms)
minidaq_exercise(e4_klein_nishina)
minidaq_exercise(e5_rates_vs_activity)


# Exercise 8.6 (A): an audit. Your tests (starter/ or solution/) run against the corrected
# change, the agent's change and each of its defects; tools/audit_exercises.py checks its record.
minidaq_python_exercise(audit-coincidence-pairs)
find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
  add_test(NAME ch08/audit-coincidence-pairs/record
           COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/audit_exercises.py ${PROJECT_SOURCE_DIR}
                   exercises/ch08/audit-coincidence-pairs)
  set_tests_properties(ch08/audit-coincidence-pairs/record PROPERTIES LABELS unit)
endif()
