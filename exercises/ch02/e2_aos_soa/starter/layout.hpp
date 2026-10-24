#pragma once
// Exercise 2.2 starter. TODO: implement to_soa() and both sum_energy() overloads.
#include <cstdint>
#include <span>
#include <vector>

namespace ex {

struct Single {  // 16 bytes, as minidaq::Single
  std::int64_t time_ps;
  std::uint32_t crystal;
  float energy_kev;
};

struct SinglesSoA {
  std::vector<std::int64_t> time_ps;
  std::vector<std::uint32_t> crystal;
  std::vector<float> energy_kev;
};

inline SinglesSoA to_soa(std::span<const Single> aos) {
  (void)aos;
  return {};  // TODO
}

inline double sum_energy(std::span<const Single> aos) {
  (void)aos;
  return 0.0;  // TODO
}

inline double sum_energy(const SinglesSoA& soa) {
  (void)soa;
  return 0.0;  // TODO
}

}  // namespace ex
