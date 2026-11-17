# SPDX-License-Identifier: MIT
# Exercise 32.4, a solution: tinylib 1.0 pinned by the SHA-256 of its archive, its headers
# included as system headers, the program's own code still built with warnings as errors.
cmake_minimum_required(VERSION 3.25)
project(usetiny LANGUAGES CXX)

set(TINY_URL "" CACHE FILEPATH "tinylib-1.0.tar, written by tests/make_archive.py")

include(FetchContent)
# The hash names the bytes: a replaced archive at the same URL fails the configure. SYSTEM makes
# tinylib's include directory a system one for its users, so our warnings do not fire in code we
# review as SOUP instead of compiling to our rules.
FetchContent_Declare(tinylib
  URL      ${TINY_URL}
  URL_HASH SHA256=829872574e743a97560d91e8b07ff73d792dd83d3391011c8896caf897294cbf
  SYSTEM)
FetchContent_MakeAvailable(tinylib)

add_executable(usetiny main.cpp)
target_compile_features(usetiny PRIVATE cxx_std_20)
target_compile_options(usetiny PRIVATE -Wall -Wextra -Wconversion -Werror)
target_link_libraries(usetiny PRIVATE tiny::tiny)
