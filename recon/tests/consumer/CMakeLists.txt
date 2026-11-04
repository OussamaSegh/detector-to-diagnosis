# SPDX-License-Identifier: MIT
# A project outside MiniDAQ that uses the installed projector library (Chapter 32). It knows
# nothing of MiniDAQ's source tree: only find_package and the imported target.
cmake_minimum_required(VERSION 3.28)
project(recon_consumer LANGUAGES CXX)

# The version this project was written for; the test cmake.consumer passes the build's own.
set(RECON_VERSION 0.8 CACHE STRING "the minor version of recon this project needs")
# [snippet:consumer]
find_package(recon ${RECON_VERSION} REQUIRED)
add_executable(consumer main.cpp)
target_link_libraries(consumer PRIVATE recon::projector)
# [/snippet:consumer]
