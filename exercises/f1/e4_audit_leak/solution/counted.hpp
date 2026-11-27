// Instance counting for Exercise F1.4: each Header and Index adds one while it lives.
#pragma once

#include <cstddef>

namespace ex {

struct Live {
  static long& headers() noexcept {
    static long n = 0;
    return n;
  }
  static long& indexes() noexcept {
    static long n = 0;
    return n;
  }
};

}  // namespace ex
