# SPDX-License-Identifier: MIT
# Toolchain file (Chapter 32): which compilers build MiniDAQ, chosen before the first
# project() call, where CMake inspects them. The presets that inherit "gcc" name this file.
set(CMAKE_C_COMPILER gcc)
set(CMAKE_CXX_COMPILER g++)
