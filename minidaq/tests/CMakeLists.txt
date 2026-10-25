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
  unit/test_run_integrity.cpp
  unit/test_control_protocol.cpp
  unit/test_security.cpp
  unit/test_audit_log.cpp
  unit/test_udp_detector.cpp
  unit/test_properties.cpp
  unit/test_service_interactions.cpp)
target_link_libraries(minidaq_unit_tests PRIVATE minidaq::control OpenSSL::SSL OpenSSL::Crypto minidaq::warnings GTest::gtest_main GTest::gmock)
# Tests that read shipped files (configurations, profiles, architecture documents).
target_compile_definitions(minidaq_unit_tests PRIVATE MINIDAQ_SOURCE_DIR="${PROJECT_SOURCE_DIR}")
# Test support shared by the unit tests and the exercises (support/property.hpp).
target_include_directories(minidaq_unit_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
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
  # Chapter 14: every source file is in a classified software item, and the classes follow the rules.
  add_test(NAME architecture.items COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/check_items.py ${PROJECT_SOURCE_DIR})
  set_tests_properties(architecture.items PROPERTIES LABELS "unit")
  # Chapter 13: the regulatory file is complete, its links resolve, its map is current.
  add_test(NAME docs.regulatory COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/check_regulatory.py ${PROJECT_SOURCE_DIR})
  set_tests_properties(docs.regulatory PROPERTIES LABELS "unit")
  # Chapter 14: requirements in testable form, every requirement traced to its verification.
  add_test(NAME docs.srs COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/req_lint.py
                                 ${PROJECT_SOURCE_DIR}/docs/regulatory/srs.md)
  add_test(NAME docs.trace COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/trace_matrix.py ${PROJECT_SOURCE_DIR} --check)
  add_test(NAME docs.soup COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/check_soup.py ${PROJECT_SOURCE_DIR})
  add_test(NAME docs.anomalies COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/anomalies.py ${PROJECT_SOURCE_DIR} --check)
  # Chapter 15: the risk file follows its criteria, and every control is implemented and verified.
  add_test(NAME docs.risk COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/check_risk.py ${PROJECT_SOURCE_DIR})
  # Chapter 16: the design and development file, document control, change requests and CAPA.
  add_test(NAME docs.design_file COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/design_file.py ${PROJECT_SOURCE_DIR} --check)
  add_test(NAME docs.changes COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/check_changes.py ${PROJECT_SOURCE_DIR})
  add_test(NAME docs.capa COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/check_capa.py ${PROJECT_SOURCE_DIR})
  # Chapter 17: the threat model.
  add_test(NAME docs.threats COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/check_threats.py ${PROJECT_SOURCE_DIR})
  # Chapter 20: the tool list is complete and its table current.
  add_test(NAME docs.tools COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/check_tools.py ${PROJECT_SOURCE_DIR} --check)
  # CAPA-0001: every sleep in a test states why (coding standard rule 5.5).
  add_test(NAME tests.waits COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/check_test_waits.py ${PROJECT_SOURCE_DIR})
  set_tests_properties(docs.srs docs.trace docs.soup docs.anomalies docs.risk docs.design_file docs.changes docs.capa
                       docs.threats docs.tools tests.waits PROPERTIES LABELS "unit")
endif()

if(Python3_Interpreter_FOUND)
  # The SBOM is generated from cmake/Dependencies.cmake and must validate
  # against the vendored CycloneDX 1.5 schema (skipped without jsonschema).
  add_test(NAME tools.sbom COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/make_sbom.py --validate ${PROJECT_SOURCE_DIR})
  set_tests_properties(tools.sbom PROPERTIES LABELS "unit" SKIP_RETURN_CODE 77)
  # Chapter 17: the triage rules for the findings of the vulnerability scan.
  add_test(NAME tools.vuln_triage COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/test_vuln_triage.py)
  set_tests_properties(tools.vuln_triage PROPERTIES LABELS "unit")
  # Chapter 20: tools whose output is release evidence are tested like code. The perf gate is
  # the solution of Exercise 5.3; its acceptance tests run against the copy in tools/ too.
  add_test(NAME tools.release_bundle
           COMMAND ${Python3_EXECUTABLE} ${PROJECT_SOURCE_DIR}/tools/test_release_bundle.py ${CMAKE_CXX_COMPILER})
  add_test(NAME tools.perf_gate
           COMMAND ${Python3_EXECUTABLE} -m unittest discover -s ${PROJECT_SOURCE_DIR}/exercises/ch05/e3_perf_gate/tests)
  set_tests_properties(tools.perf_gate PROPERTIES
    ENVIRONMENT "PYTHONPATH=${PROJECT_SOURCE_DIR}/tools;PYTHONDONTWRITEBYTECODE=1")
  set_tests_properties(tools.release_bundle tools.perf_gate PROPERTIES LABELS "unit")
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

# Chapter 19: system tests. Each file runs the shipped programs (minidaq_server, minidaq_ctl,
# minidaq_send, minidaq_listmode) in their own processes, as an operator would.
if(Python3_Interpreter_FOUND)
  set(_time_factor 1)
  if(MINIDAQ_SANITIZERS)
    set(_time_factor 10)  # sanitized programs run several times slower; the deadlines stretch
  endif()
  foreach(name control acquisition readout)
    add_test(NAME system.${name}
             COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/system/test_${name}_system.py)
    set_tests_properties(system.${name} PROPERTIES LABELS "system" TIMEOUT 900
      ENVIRONMENT "MINIDAQ_APPS=$<TARGET_FILE_DIR:minidaq_server>;MINIDAQ_TEST_TIME_FACTOR=${_time_factor}")
  endforeach()
  # The statistics the system tests rely on, against tabulated values and for calibration.
  add_test(NAME system.stats COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/system/test_stats.py)
  set_tests_properties(system.stats PROPERTIES LABELS "unit")
endif()
