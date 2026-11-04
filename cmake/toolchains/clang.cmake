# SPDX-License-Identifier: MIT
# Toolchain file (Chapter 32): Clang for C and C++. The presets that inherit "clang" name this
# file. A cross toolchain file adds CMAKE_SYSTEM_NAME, CMAKE_SYSTEM_PROCESSOR, a sysroot and
# where find_package may look (see Chapter 32); this one only chooses the compilers.
set(CMAKE_C_COMPILER clang)
set(CMAKE_CXX_COMPILER clang++)
