# SPDX-License-Identifier: MIT
# Exercise 32.1, solution: the library pulse, installable as a CMake package.
cmake_minimum_required(VERSION 3.25)
project(pulse VERSION 1.2.0 LANGUAGES CXX)
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

add_library(pulse src/pulse.cpp)
add_library(pulse::pulse ALIAS pulse)
target_compile_features(pulse PUBLIC cxx_std_20)
# The headers are in the source tree while building and under the prefix once installed.
target_include_directories(pulse PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)
# How the library is built: its users do not inherit it.
target_compile_definitions(pulse PRIVATE PULSE_CHECKED=1)

set(config_dir ${CMAKE_INSTALL_LIBDIR}/cmake/pulse)
install(TARGETS pulse EXPORT pulseTargets
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(DIRECTORY include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(EXPORT pulseTargets NAMESPACE pulse:: DESTINATION ${config_dir})
configure_package_config_file(cmake/pulseConfig.cmake.in
  ${CMAKE_CURRENT_BINARY_DIR}/pulseConfig.cmake INSTALL_DESTINATION ${config_dir})
# 1.2 satisfies a request for 1.0 or 1.1, not one for 2.0: a new major version may break users.
write_basic_package_version_file(${CMAKE_CURRENT_BINARY_DIR}/pulseConfigVersion.cmake
  COMPATIBILITY SameMajorVersion)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/pulseConfig.cmake
              ${CMAKE_CURRENT_BINARY_DIR}/pulseConfigVersion.cmake
        DESTINATION ${config_dir})
