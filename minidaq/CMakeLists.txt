# MiniDAQ library and applications.
add_library(minidaq_core
  src/format/raw_single.cpp
  src/format/packed_single.cpp
  src/format/readout_packet.cpp
  src/format/list_mode.cpp
  src/core/crc32.cpp
  src/core/flight_recorder.cpp
  src/pipeline/acquisition_pipeline.cpp
  src/processing/energy_filter.cpp
  src/processing/calibration.cpp
  src/processing/singles_counter.cpp
  src/processing/coincidence_sorter.cpp
  src/processing/sinogram.cpp
  src/processing/stream_merger.cpp
  src/rt/realtime.cpp
  src/rt/crash_report.cpp
  src/rt/health.cpp
  src/hw/register.cpp
  src/hw/mmio_bus.cpp
  src/hw/slow_control.cpp
  src/net/host_counters.cpp)
add_library(minidaq::core ALIAS minidaq_core)
target_include_directories(minidaq_core PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>)
target_compile_features(minidaq_core PUBLIC cxx_std_23)
find_package(Threads REQUIRED)
target_link_libraries(minidaq_core PUBLIC Threads::Threads PRIVATE minidaq::warnings)

# The simulator (CR-0029): the synthetic source, the detector simulator, the readout link and the
# simulated front-end board. The development programs, the tests and the benchmarks link it; the
# server links it only with MINIDAQ_WITH_SIMULATOR, so that the product contains none of it.
# (Target minidaq_simulation: minidaq_sim is the program of Chapter 12.)
add_library(minidaq_simulation
  src/sim/synthetic_source.cpp
  src/sim/detector_simulator.cpp
  src/sim/truth_counter.cpp
  src/sim/readout_link.cpp
  src/sim/dead_time.cpp
  src/hw/fake_board.cpp)
add_library(minidaq::sim ALIAS minidaq_simulation)
target_link_libraries(minidaq_simulation PUBLIC minidaq::core PRIVATE minidaq::warnings)

# Ed25519 signatures and SHA-256 (ADR 0020, ADR 0034): shared by the update tool, which verifies
# bundles, and the server, which signs run records and verifies calibration tables.
add_library(minidaq_signing src/control/signing.cpp)
add_library(minidaq::signing ALIAS minidaq_signing)
target_link_libraries(minidaq_signing PUBLIC minidaq::core PRIVATE OpenSSL::Crypto minidaq::warnings)

# The control plane (Chapter 6): configuration, state machine, service, control
# API. A separate library so that the hot-path core does not depend on JSON.
add_library(minidaq_control
  src/config/acquisition_config.cpp
  src/config/hardware_config.cpp
  src/config/calibration_file.cpp
  src/control/access.cpp
  src/control/acquisition_state.cpp
  src/control/adapters.cpp
  src/control/hardware.cpp
  src/control/audit.cpp
  src/control/audit_log.cpp
  src/control/acquisition_service.cpp
  src/control/run_integrity.cpp
  src/control/corrections_record.cpp
  src/control/tls.cpp
  src/control/control_protocol.cpp
  src/control/control_server.cpp
  src/control/udp_detector.cpp
  src/control/file_ops.cpp
  src/control/listmode_sink.cpp
  src/control/service_manager.cpp)
add_library(minidaq::control ALIAS minidaq_control)
target_link_libraries(minidaq_control PUBLIC minidaq::core minidaq::signing nlohmann_json::nlohmann_json
                      PRIVATE OpenSSL::SSL OpenSSL::Crypto minidaq::warnings)
target_compile_definitions(minidaq_control PRIVATE MINIDAQ_VERSION_STRING="${MINIDAQ_VERSION_FULL}"
                           PUBLIC MINIDAQ_WITH_SIMULATOR=$<BOOL:${MINIDAQ_WITH_SIMULATOR}>)
if(MINIDAQ_WITH_SIMULATOR)
  target_link_libraries(minidaq_control PRIVATE minidaq::sim)
endif()

# Chapter 25: signed updates into two slots, with rollback (ADR 0020). Its own library: only
# minidaq_update links it, and the server knows nothing of updates.
add_library(minidaq_update_lib
  src/update/bundle.cpp
  src/update/slots.cpp)
add_library(minidaq::update ALIAS minidaq_update_lib)
target_link_libraries(minidaq_update_lib PUBLIC minidaq::core
                      PRIVATE minidaq::signing nlohmann_json::nlohmann_json OpenSSL::Crypto minidaq::warnings)

add_subdirectory(apps)

if(MINIDAQ_BUILD_TESTS)
  add_subdirectory(tests)
endif()
