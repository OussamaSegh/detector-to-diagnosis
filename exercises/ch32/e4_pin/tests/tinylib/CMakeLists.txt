# SPDX-License-Identifier: MIT
# tinylib 1.0: a header-only dependency for Exercise 32.4, fetched from an archive.
cmake_minimum_required(VERSION 3.25)
project(tinylib VERSION 1.0 LANGUAGES CXX)
add_library(tiny INTERFACE)
add_library(tiny::tiny ALIAS tiny)
target_include_directories(tiny INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/include)
