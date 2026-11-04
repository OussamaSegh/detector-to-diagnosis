# SPDX-License-Identifier: MIT
# Exercise 32.2: a small library with its tests. The project is complete; the exercise is its
# CMakePresets.json.
cmake_minimum_required(VERSION 3.25)
project(window LANGUAGES CXX)
add_library(window src/window.cpp)
target_include_directories(window PUBLIC src)
target_compile_features(window PUBLIC cxx_std_20)
enable_testing()
add_executable(window_test src/window_test.cpp)
target_link_libraries(window_test PRIVATE window)
add_test(NAME window.sums COMMAND window_test sums)
add_test(NAME window.edges COMMAND window_test edges)
