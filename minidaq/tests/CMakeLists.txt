# Unit tests. Each test file carries requirement tags (REQ: ...) that
# tools/trace_matrix.py collects into the traceability matrix (Chapter 14).
add_executable(minidaq_unit_tests
  unit/test_quantity.cpp
  unit/test_expected.cpp
  unit/test_geometry.cpp
  unit/test_raw_single.cpp
  unit/test_packed_single.cpp
  unit/test_spsc_ring.cpp
  unit/test_mpmc_queue.cpp
  unit/test_channel.cpp
  unit/test_pipeline.cpp
  unit/test_memory_model.cpp
  unit/test_latency_histogram.cpp
  unit/test_realtime.cpp
  unit/test_paced_source.cpp)
target_link_libraries(minidaq_unit_tests PRIVATE minidaq::core minidaq::warnings GTest::gtest_main)
gtest_discover_tests(minidaq_unit_tests PROPERTIES LABELS "unit")

# Separate binary: it replaces global operator new to count allocations.
# Not built under ASan, which needs its own allocator.
if(NOT MINIDAQ_SANITIZERS)
  add_executable(minidaq_alloc_tests unit/test_zero_alloc.cpp)
  target_link_libraries(minidaq_alloc_tests PRIVATE minidaq::core minidaq::warnings GTest::gtest_main)
  gtest_discover_tests(minidaq_alloc_tests PROPERTIES LABELS "unit")
endif()
