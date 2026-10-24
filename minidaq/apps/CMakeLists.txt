# Command-line tools built on the MiniDAQ library.
foreach(app minidaq_jitter minidaq_latency)
  add_executable(${app} ${app}.cpp)
  target_link_libraries(${app} PRIVATE minidaq::core minidaq::warnings)
endforeach()
