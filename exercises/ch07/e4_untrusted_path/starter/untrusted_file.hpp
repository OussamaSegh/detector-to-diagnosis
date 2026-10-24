// SPDX-License-Identifier: MIT
// Exercise 7.4: read a file whose name came from outside the program (a
// control client, a configuration), without letting that name hurt you.
#pragma once

#include <cstddef>
#include <string>

#include "minidaq/core/expected.hpp"

namespace ex74 {

// Returns the contents of `path`, or a message naming the path and the reason.
// Accepts only a regular file of at most `max_bytes` that is not a symbolic
// link and not writable by every user; never blocks on a FIFO or a device.
[[nodiscard]] minidaq::Expected<std::string, std::string> read_untrusted_file(const std::string& path,
                                                                             std::size_t max_bytes);

}  // namespace ex74
