# SPDX-License-Identifier: MIT
# Exercise 32.1, starter: the library pulse builds and installs its files, but a project that
# calls find_package(pulse) does not find it. Make it an installable CMake package.
cmake_minimum_required(VERSION 3.25)
project(pulse VERSION 1.2.0 LANGUAGES CXX)

add_library(pulse src/pulse.cpp)
add_library(pulse::pulse ALIAS pulse)
target_compile_features(pulse PUBLIC cxx_std_20)
# TODO(1): this path is right while building and wrong once installed: the source tree may be
# gone, and install(EXPORT) refuses a target whose interface names it.
target_include_directories(pulse PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
# TODO(2): PULSE_CHECKED is how this library is built. Should its users compile with it?
target_compile_definitions(pulse PUBLIC PULSE_CHECKED=1)

install(TARGETS pulse ARCHIVE DESTINATION lib LIBRARY DESTINATION lib)
install(DIRECTORY include/ DESTINATION include)
# TODO(3): install an export set of the target under the namespace pulse::, a package
# configuration file that includes it, and a version file that accepts 1.x and refuses 2.0.
