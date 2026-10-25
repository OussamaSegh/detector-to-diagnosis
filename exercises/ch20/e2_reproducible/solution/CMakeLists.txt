# SPDX-License-Identifier: MIT
# Exercise 20.2 solution: the same program, built reproducibly.
cmake_minimum_required(VERSION 3.20)
project(reproducible_demo VERSION 1.0 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
# [snippet:maps]
# Paths in __FILE__ and in the debug information, relative to the top of the sources (and of the
# build directory, which may lie inside them: GCC takes the last matching map, Clang the longest).
add_compile_options("-ffile-prefix-map=${CMAKE_SOURCE_DIR}/="
                    "-ffile-prefix-map=${CMAKE_BINARY_DIR}/=build/")
# [/snippet:maps]
add_executable(demo src/main.cpp src/build_info.cpp)
# The version comes from the project, not from the clock; the commit identifies the build.
target_compile_definitions(demo PRIVATE DEMO_VERSION="${PROJECT_VERSION}")
