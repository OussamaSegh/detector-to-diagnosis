#pragma once
// Exercise 2.3 starter: allocates a fresh vector for every batch.
// TODO: give the stage a monotonic arena created once, reset per batch, and
// reject batches larger than the capacity.
#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

#include "minidaq/core/expected.hpp"

namespace ex {

struct Single {
  std::int64_t time_ps;
  std::uint32_t crystal;
  float energy_kev;
};

enum class StageError { batch_too_large };

class EnergyWindowStage {
 public:
  EnergyWindowStage(float lo_kev, float hi_kev, std::size_t capacity)
      : lo_{lo_kev}, hi_{hi_kev}, capacity_{capacity} {}

  minidaq::Expected<std::span<const Single>, StageError> process(std::span<const Single> in) {
    out_ = std::vector<Single>{};  // TODO: this allocates on every batch
    for (const Single& s : in) {
      if (s.energy_kev >= lo_ && s.energy_kev <= hi_) {
        out_.push_back(s);
      }
    }
    return std::span<const Single>{out_};
  }

 private:
  float lo_;
  float hi_;
  std::size_t capacity_;
  std::vector<Single> out_;
};

}  // namespace ex
