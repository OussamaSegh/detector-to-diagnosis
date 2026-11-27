minidaq_python_exercise(e1_where_dropped)
minidaq_exercise(e2_rxq_ovfl)
minidaq_exercise(e3_buffer_sizing)
minidaq_exercise(e4_batch_receiver)

# Exercise 23.5 (A): an audit. Your tests (starter/ or solution/) run against the
# corrected change (original), the agent's change (mutant_1) and each of its
# defects (mutant_2 and up); tools/audit_exercises.py checks its record.
minidaq_mutation_exercise(audit-loss-counter MUTANTS 3)
find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
  add_test(NAME ch23/audit-loss-counter/record
           COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/audit_exercises.py ${PROJECT_SOURCE_DIR}
                   exercises/ch23/audit-loss-counter)
  set_tests_properties(ch23/audit-loss-counter/record PROPERTIES LABELS unit)
endif()
