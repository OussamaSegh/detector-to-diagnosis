// SPDX-License-Identifier: MIT
// Review of 2.2.0: hashes the synthetic source's words, to compare two builds (README.md).
#include <cstdio>
#include <vector>
#include "minidaq/sim/synthetic_source.hpp"
int main() {
  for (unsigned long long seed : {1ULL, 7ULL}) {
    minidaq::sim::SyntheticConfig c{};
    c.seed = seed;
    minidaq::sim::SyntheticSource g{c};
    std::vector<std::uint64_t> w(1u << 22);
    g.generate(w);
    unsigned long long h = 1469598103934665603ULL;
    for (auto x : w) {
      h ^= x;
      h *= 1099511628211ULL;
    }
    std::printf("seed %llu fnv %016llx\n", seed, h);
  }
  minidaq::sim::SyntheticSource g{{}};
  std::vector<std::uint64_t> w(1u << 22);
  g.generate(w);
  unsigned long long h = 1469598103934665603ULL;
  for (auto x : w) {
    h ^= x;
    h *= 1099511628211ULL;
  }
  std::printf("default {} fnv %016llx\n", h);
}
