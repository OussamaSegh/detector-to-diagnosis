// SPDX-License-Identifier: MIT
// Exercise 32.4: a program that uses tinylib, fetched from an archive.
#include <iostream>

#include <tiny/scale.hpp>

int main() {
  std::cout << "scaled " << tiny::scaled(2.5, 4.0) << '\n';
  return 0;
}
