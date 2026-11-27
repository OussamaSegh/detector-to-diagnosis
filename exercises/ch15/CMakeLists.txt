minidaq_python_exercise(e1_hazard_chains)
minidaq_exercise(e2_loss_controls)
minidaq_python_exercise(e3_sorter_fmea)
minidaq_python_exercise(e4_fault_tree)
minidaq_python_exercise(e5_residual_risk)

# Exercise 15.6 (A): an audit. Your tests (starter/ or solution/) run against the
# corrected change (original), the agent's change (mutant_1) and each of its
# defects (mutant_2 and up); tools/audit_exercises.py checks its record.
minidaq_mutation_exercise(audit-fault-latch MUTANTS 3)
find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
  add_test(NAME ch15/audit-fault-latch/record
           COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/audit_exercises.py ${PROJECT_SOURCE_DIR}
                   exercises/ch15/audit-fault-latch)
  set_tests_properties(ch15/audit-fault-latch/record PROPERTIES LABELS unit)
endif()
