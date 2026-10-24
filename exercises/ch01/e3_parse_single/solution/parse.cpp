#include "parse.hpp"

#include <bit>
#include <cmath>
#include <cstring>

namespace ex {

namespace {
constexpr std::size_t kRecordSize = 16;
constexpr std::uint32_t kNumCrystals = 18432;
constexpr float kMaxEnergyKeV = 2000.0F;

template <typename T>
T load(const std::byte* p) noexcept {
  static_assert(std::endian::native == std::endian::little, "add a byteswap for big-endian hosts");
  T v;
  std::memcpy(&v, p, sizeof v);
  return v;
}
}  // namespace

minidaq::Expected<Single, ParseError> parse_single(std::span<const std::byte> bytes) noexcept {
  if (bytes.size() < kRecordSize) {
    return minidaq::Unexpected{ParseError::truncated};
  }
  const auto time = load<std::int64_t>(bytes.data());
  const auto crystal = load<std::uint32_t>(bytes.data() + 8);
  const auto energy = load<float>(bytes.data() + 12);

  if (time < 0) {
    return minidaq::Unexpected{ParseError::negative_time};
  }
  if (crystal >= kNumCrystals) {
    return minidaq::Unexpected{ParseError::crystal_out_of_range};
  }
  if (!std::isfinite(energy)) {  // must come before the range check: NaN compares false
    return minidaq::Unexpected{ParseError::energy_not_finite};
  }
  if (energy < 0.0F || energy > kMaxEnergyKeV) {
    return minidaq::Unexpected{ParseError::energy_out_of_range};
  }
  return Single{time, crystal, energy};
}

}  // namespace ex
