// SPDX-License-Identifier: MIT
#include "batch_receiver.hpp"

#include <cerrno>
#include <cstring>
#include <stdexcept>

namespace rx {

BatchReceiver::BatchReceiver(int fd, std::size_t batch, std::size_t max_datagram)
    : fd_{fd},
      batch_{batch},
      slot_{max_datagram + 1},
      data_(batch * slot_),
      control_(batch * control_bytes),
      iov_(batch),
      msgs_(batch) {
  if (batch == 0 || max_datagram == 0) {
    throw std::invalid_argument{"BatchReceiver: batch and max_datagram must be positive"};
  }
}

std::size_t BatchReceiver::receive() {
  // The kernel writes msg_len, msg_flags and msg_controllen back, so the headers are set again
  // before each call; the buffers they point to stay where they are.
  for (std::size_t i = 0; i < batch_; ++i) {
    iov_[i] = {data_.data() + i * slot_, slot_};
    msgs_[i] = {};
    msgs_[i].msg_hdr.msg_iov = &iov_[i];
    msgs_[i].msg_hdr.msg_iovlen = 1;
    msgs_[i].msg_hdr.msg_control = control_.data() + i * control_bytes;
    msgs_[i].msg_hdr.msg_controllen = control_bytes;
  }
  ++calls_;
  const int n = ::recvmmsg(fd_, msgs_.data(), static_cast<unsigned>(batch_), MSG_DONTWAIT, nullptr);
  if (n < 0) {
    if (errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) {
      error_ = errno;
    }
    received_ = 0;
    return 0;
  }
  received_ = static_cast<std::size_t>(n);
  return received_;
}

std::span<const std::byte> BatchReceiver::datagram(std::size_t i) const {
  if (i >= received_) {
    throw std::out_of_range{"BatchReceiver::datagram"};
  }
  const std::size_t len = std::min<std::size_t>(msgs_[i].msg_len, slot_ - 1);
  return std::span<const std::byte>{data_}.subspan(i * slot_, len);
}

bool BatchReceiver::truncated(std::size_t i) const {
  if (i >= received_) {
    throw std::out_of_range{"BatchReceiver::truncated"};
  }
  // A datagram that filled the extra byte, or that the kernel cut (MSG_TRUNC), was too long.
  return msgs_[i].msg_len >= slot_ || (msgs_[i].msg_hdr.msg_flags & MSG_TRUNC) != 0;
}

std::uint32_t BatchReceiver::drops_when_queued(std::size_t i) const {
  if (i >= received_) {
    throw std::out_of_range{"BatchReceiver::drops_when_queued"};
  }
  const msghdr& h = msgs_[i].msg_hdr;
  // NOLINTBEGIN(cppcoreguidelines-pro-type-reinterpret-cast,cppcoreguidelines-pro-bounds-pointer-arithmetic,cppcoreguidelines-pro-type-const-cast)
  for (cmsghdr* c = CMSG_FIRSTHDR(&h); c != nullptr; c = CMSG_NXTHDR(const_cast<msghdr*>(&h), c)) {
    if (c->cmsg_level == SOL_SOCKET && c->cmsg_type == SO_RXQ_OVFL &&
        c->cmsg_len >= CMSG_LEN(sizeof(std::uint32_t))) {
      std::uint32_t v = 0;
      std::memcpy(&v, CMSG_DATA(c), sizeof v);
      return v;
    }
  }
  // NOLINTEND(cppcoreguidelines-pro-type-reinterpret-cast,cppcoreguidelines-pro-bounds-pointer-arithmetic,cppcoreguidelines-pro-type-const-cast)
  return 0;
}

}  // namespace rx
