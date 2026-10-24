#pragma once
// Exercise 2.3 solution: one arena, allocated once; each batch resets it.
#include <cstddef>
#include <cstdint>
#include <memory_resource>
#include <optional>
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
      : lo_{lo_kev}, hi_{hi_kev}, capacity_{capacity}, arena_(capacity * sizeof(Single) + kSlack) {}

  minidaq::Expected<std::span<const Single>, StageError> process(std::span<const Single> in) {
    if (in.size() > capacity_) {
      return minidaq::Unexpected{StageError::batch_too_large};
    }
    // Destroy the previous batch's vector before resetting the arena it lives in.
    out_.reset();
    resource_.emplace(arena_.data(), arena_.size(), std::pmr::null_memory_resource());
    out_.emplace(&*resource_);
    out_->reserve(in.size());  // one bump allocation, never a regrowth
    for (const Single& s : in) {
      if (s.energy_kev >= lo_ && s.energy_kev <= hi_) {
        out_->push_back(s);
      }
    }
    return std::span<const Single>{*out_};
  }

 private:
  static constexpr std::size_t kSlack = 64;  // alignment headroom
  float lo_;
  float hi_;
  std::size_t capacity_;
  std::vector<std::byte> arena_;  // the only heap allocation, made once
  std::optional<std::pmr::monotonic_buffer_resource> resource_;
  std::optional<std::pmr::vector<Single>> out_;
};

}  // namespace ex
