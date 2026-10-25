// SPDX-License-Identifier: MIT
#include <cstdio>

const char* build_info();

#define LOG(msg) std::printf("%s:%d: %s\n", __FILE__, __LINE__, msg)

int main() {
  std::printf("%s\n", build_info());
  LOG("starting");
  return 0;
}
