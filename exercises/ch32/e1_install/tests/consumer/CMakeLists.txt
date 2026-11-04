# SPDX-License-Identifier: MIT
# Uses an installed pulse as any other project would: through find_package, with nothing of the
# pulse build on its paths.
cmake_minimum_required(VERSION 3.25)
project(consumer LANGUAGES CXX)
set(PULSE_VERSION 1.2 CACHE STRING "the version of pulse to ask for")
find_package(pulse ${PULSE_VERSION} REQUIRED)
add_executable(consumer main.cpp)
target_link_libraries(consumer PRIVATE pulse::pulse)
