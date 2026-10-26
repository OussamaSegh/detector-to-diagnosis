// SPDX-License-Identifier: MIT
#include "tiny_recorder.hpp"

namespace ex21 {

void TinyRecorder::record(std::uint64_t a, std::uint64_t b) noexcept {
  // TODO: write event number next_ + 1 into its slot so that a reader can never take half of it,
  // then publish it.
  (void)a;
  (void)b;
}

std::size_t TinyRecorder::snapshot(std::span<Event> out) const noexcept {
  // TODO: copy the newest complete events, oldest first. Skip (and count in torn_) a slot whose
  // event changed while you copied it.
  (void)out;
  return 0;
}

}  // namespace ex21
