# SPDX-License-Identifier: MIT
# A project outside MiniDAQ that uses the installed projector library (Chapter 32). It knows
# nothing of MiniDAQ's source tree: only find_package and the imported target.
cmake_minimum_required(VERSION 3.28)
project(recon_consumer LANGUAGES CXX)

# [snippet:consumer]
find_package(recon 0.7 REQUIRED)
add_executable(consumer main.cpp)
target_link_libraries(consumer PRIVATE recon::projector)
# [/snippet:consumer]
