# Command-line tools built on the MiniDAQ library.
foreach(app minidaq_jitter minidaq_latency minidaq_send)
  add_executable(${app} ${app}.cpp)
  target_link_libraries(${app} PRIVATE minidaq::core minidaq::warnings)
endforeach()

# Control plane (Chapter 6).
add_executable(minidaq_server minidaq_server.cpp)
target_link_libraries(minidaq_server PRIVATE minidaq::control minidaq::warnings)
target_compile_definitions(minidaq_server PRIVATE MINIDAQ_VERSION_STRING="${MINIDAQ_VERSION_FULL}")
add_executable(minidaq_ctl minidaq_ctl.cpp)
target_link_libraries(minidaq_ctl PRIVATE minidaq::control minidaq::warnings)

# Chapter 12: minidaq_sim writes list mode with the DAQ's own sink.
add_executable(minidaq_sim minidaq_sim.cpp)
target_link_libraries(minidaq_sim PRIVATE minidaq::control minidaq::warnings)
add_executable(minidaq_listmode minidaq_listmode.cpp)
target_link_libraries(minidaq_listmode PRIVATE minidaq::core nlohmann_json::nlohmann_json minidaq::warnings)

# Chapter 25: signed updates with rollback, outside the slots it updates.
add_executable(minidaq_update minidaq_update.cpp)
target_link_libraries(minidaq_update PRIVATE minidaq::update nlohmann_json::nlohmann_json minidaq::warnings)
