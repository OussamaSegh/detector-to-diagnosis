// SPDX-License-Identifier: MIT
#include "batch_receiver.hpp"

#include <stdexcept>

namespace rx {

BatchReceiver::BatchReceiver(int fd, std::size_t batch, std::size_t max_datagram)
    : fd_{fd}, batch_{batch}, slot_{max_datagram + 1} {
  // TODO: allocate every buffer here (data, control, iovecs, message headers), and refuse a
  // batch or a datagram size of 0.
}

std::size_t BatchReceiver::receive() {
  // TODO: set up the message headers, call recvmmsg with MSG_DONTWAIT, keep errno unless it is
  // EAGAIN, EWOULDBLOCK or EINTR.
  ++calls_;
  return 0;
}

std::span<const std::byte> BatchReceiver::datagram(std::size_t i) const {
  // TODO
  (void)i;
  return {};
}

bool BatchReceiver::truncated(std::size_t i) const {
  // TODO
  (void)i;
  return false;
}

std::uint32_t BatchReceiver::drops_when_queued(std::size_t i) const {
  // TODO: the SO_RXQ_OVFL control message of this datagram (Exercise 23.2).
  (void)i;
  return 0;
}

}  // namespace rx
