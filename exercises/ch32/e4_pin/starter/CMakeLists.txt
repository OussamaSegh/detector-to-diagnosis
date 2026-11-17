# SPDX-License-Identifier: MIT
# Exercise 32.4: fetch tinylib 1.0 from its archive and build a program with it, warnings as errors.
# TODO: make the tests pass.
cmake_minimum_required(VERSION 3.25)
project(usetiny LANGUAGES CXX)

set(TINY_URL "" CACHE FILEPATH "tinylib-1.0.tar, written by tests/make_archive.py")

include(FetchContent)
FetchContent_Declare(tinylib
  URL ${TINY_URL})
FetchContent_MakeAvailable(tinylib)

add_executable(usetiny main.cpp)
target_compile_features(usetiny PRIVATE cxx_std_20)
target_compile_options(usetiny PRIVATE -Wall -Wextra -Wconversion -Werror)
target_link_libraries(usetiny PRIVATE tiny::tiny)
