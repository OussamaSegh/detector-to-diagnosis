#include "parse.hpp"

namespace ex {

minidaq::Expected<Single, ParseError> parse_single(std::span<const std::byte> bytes) noexcept {
  // TODO: check the length, decode the three fields with std::memcpy,
  // validate each one and return minidaq::Unexpected{ParseError::...} on failure.
  (void)bytes;
  return minidaq::Unexpected{ParseError::truncated};
}

}  // namespace ex
