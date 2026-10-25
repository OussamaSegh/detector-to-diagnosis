# SPDX-License-Identifier: MIT
# Exercise 20.2 starter: a small program whose build is not reproducible.
cmake_minimum_required(VERSION 3.20)
project(reproducible_demo VERSION 1.0 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
add_executable(demo src/main.cpp src/build_info.cpp)
