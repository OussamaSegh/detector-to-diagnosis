# SPDX-License-Identifier: MIT
# Exercise 32.3: a program of eleven sources. Touching config.hpp should not rebuild them all.
cmake_minimum_required(VERSION 3.25)
project(rings LANGUAGES CXX)
add_executable(rings src/main.cpp src/config.cpp src/geometry.cpp
  src/ring_0.cpp src/ring_1.cpp src/ring_2.cpp src/ring_3.cpp
  src/ring_4.cpp src/ring_5.cpp src/ring_6.cpp src/ring_7.cpp)
target_compile_features(rings PRIVATE cxx_std_20)
