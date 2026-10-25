# Unit tests. Each test file carries requirement tags (REQ: ...) that
# tools/trace_matrix.py collects into the traceability matrix (Chapter 14).
add_executable(minidaq_unit_tests
  unit/test_quantity.cpp
  unit/test_parse_number.cpp
  unit/test_expected.cpp
  unit/test_geometry.cpp
  unit/test_raw_single.cpp
  unit/test_packed_single.cpp
  unit/test_readout_packet.cpp
  unit/test_crc32.cpp
  unit/test_list_mode.cpp
  unit/test_listmode_sink.cpp
  unit/test_coincidence_sorter.cpp
  unit/test_sinogram.cpp
  unit/test_stream_merger.cpp
  unit/test_dead_time.cpp
  unit/test_count_rates.cpp
  unit/test_replay_source.cpp
  unit/test_spsc_ring.cpp
  unit/test_mpmc_queue.cpp
  unit/test_channel.cpp
  unit/test_pipeline.cpp
  unit/test_memory_model.cpp
  unit/test_latency_histogram.cpp
  unit/test_realtime.cpp
  unit/test_paced_source.cpp
  unit/test_energy_filter.cpp
  unit/test_physics.cpp
  unit/test_detector_simulator.cpp
  unit/test_acquisition_state.cpp
  unit/test_config.cpp
  unit/test_acquisition_service.cpp
  unit/test_control_protocol.cpp
  unit/test_audit_log.cpp
  unit/test_udp_detector.cpp)
target_link_libraries(minidaq_unit_tests PRIVATE minidaq::control minidaq::warnings GTest::gtest_main)
# Tests that read shipped files (configurations, profiles, architecture documents).
target_compile_definitions(minidaq_unit_tests PRIVATE MINIDAQ_SOURCE_DIR="${PROJECT_SOURCE_DIR}")
gtest_discover_tests(minidaq_unit_tests PROPERTIES LABELS "unit")

# Separate binary: it replaces global operator new to count allocations.
# Not built under ASan, which needs its own allocator.
if(NOT MINIDAQ_SANITIZERS)
  add_executable(minidaq_alloc_tests unit/test_zero_alloc.cpp)
  target_link_libraries(minidaq_alloc_tests PRIVATE minidaq::core minidaq::warnings GTest::gtest_main)
  gtest_discover_tests(minidaq_alloc_tests PROPERTIES LABELS "unit")
endif()

# Architecture rule: includes respect the layers (docs/architecture/layers.json).
find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
  add_test(NAME architecture.layers COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/check_layers.py ${PROJECT_SOURCE_DIR})
  set_tests_properties(architecture.layers PROPERTIES LABELS "unit")
  # Chapter 13: the regulatory file is complete, its links resolve, its map is current.
  add_test(NAME docs.regulatory COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/check_regulatory.py ${PROJECT_SOURCE_DIR})
  set_tests_properties(docs.regulatory PROPERTIES LABELS "unit")
endif()

if(Python3_Interpreter_FOUND)
  # The SBOM is generated from cmake/Dependencies.cmake and must validate
  # against the vendored CycloneDX 1.5 schema (skipped without jsonschema).
  add_test(NAME tools.sbom COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/make_sbom.py --validate ${PROJECT_SOURCE_DIR})
  set_tests_properties(tools.sbom PROPERTIES LABELS "unit" SKIP_RETURN_CODE 77)
  # Chapter 12: the list-mode tools end to end (simulate, write, verify, damage, histogram).
  add_test(NAME tools.listmode
           COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/test_listmode_tools.py $<TARGET_FILE_DIR:minidaq_sim>)
  set_tests_properties(tools.listmode PROPERTIES LABELS "unit" TIMEOUT 300)
  # A hardened build must produce hardened binaries: read them, do not trust the flags.
  if(MINIDAQ_HARDENING)
    add_test(NAME build.hardening
      COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/check_hardening.py
              $<TARGET_FILE:minidaq_server> $<TARGET_FILE:minidaq_ctl> $<TARGET_FILE:minidaq_latency>
              $<TARGET_FILE:minidaq_jitter> $<TARGET_FILE:minidaq_listmode> $<TARGET_FILE:minidaq_unit_tests>)
    set_tests_properties(build.hardening PROPERTIES LABELS "unit")
  endif()
endif()
