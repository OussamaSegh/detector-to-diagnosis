#pragma once
// Exercise 2.2 solution. See NOTES.md for the measurements.
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
  SinglesSoA soa;
  soa.time_ps.reserve(aos.size());
  soa.crystal.reserve(aos.size());
  soa.energy_kev.reserve(aos.size());
  for (const Single& s : aos) {
    soa.time_ps.push_back(s.time_ps);
    soa.crystal.push_back(s.crystal);
    soa.energy_kev.push_back(s.energy_kev);
  }
  return soa;
}

// Each loop reads only what it needs: 16 bytes per event for AoS (the whole
// struct comes in with the cache line), 4 bytes per event for SoA.
inline double sum_energy(std::span<const Single> aos) {
  double sum = 0.0;
  for (const Single& s : aos) {
    sum += static_cast<double>(s.energy_kev);
  }
  return sum;
}

inline double sum_energy(const SinglesSoA& soa) {
  double sum = 0.0;
  for (const float e : soa.energy_kev) {
    sum += static_cast<double>(e);
  }
  return sum;
}

}  // namespace ex
