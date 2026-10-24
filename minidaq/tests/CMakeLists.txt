# Unit tests. Each test file carries requirement tags (REQ: ...) that
# tools/trace_matrix.py collects into the traceability matrix (Chapter 14).
add_executable(minidaq_unit_tests
  unit/test_quantity.cpp
  unit/test_expected.cpp
  unit/test_geometry.cpp
  unit/test_raw_single.cpp)
target_link_libraries(minidaq_unit_tests PRIVATE minidaq::core minidaq::warnings GTest::gtest_main)
gtest_discover_tests(minidaq_unit_tests PROPERTIES LABELS "unit")
