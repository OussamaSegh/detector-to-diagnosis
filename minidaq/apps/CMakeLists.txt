# Command-line tools built on the MiniDAQ library.
foreach(app minidaq_jitter minidaq_latency)
  add_executable(${app} ${app}.cpp)
  target_link_libraries(${app} PRIVATE minidaq::core minidaq::warnings)
endforeach()

# Control plane (Chapter 6).
add_executable(minidaq_server minidaq_server.cpp)
target_link_libraries(minidaq_server PRIVATE minidaq::control minidaq::warnings)
add_executable(minidaq_ctl minidaq_ctl.cpp)
target_link_libraries(minidaq_ctl PRIVATE minidaq::core nlohmann_json::nlohmann_json minidaq::warnings)
