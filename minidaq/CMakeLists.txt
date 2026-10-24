# MiniDAQ library and applications.
add_library(minidaq_core
  src/format/raw_single.cpp
  src/format/packed_single.cpp)
add_library(minidaq::core ALIAS minidaq_core)
target_include_directories(minidaq_core PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>)
target_compile_features(minidaq_core PUBLIC cxx_std_20)
target_link_libraries(minidaq_core PRIVATE minidaq::warnings)

if(MINIDAQ_BUILD_TESTS)
  add_subdirectory(tests)
endif()
