// SPDX-License-Identifier: MIT
#include "semver.hpp"

#include <tuple>

namespace semver {

std::optional<Version> parse(std::string_view text) {
  // TODO: this reads three numbers and the rest as one pre-release string, and checks nothing.
  Version v;
  std::size_t pos = 0;
  for (std::uint64_t* part : {&v.major, &v.minor, &v.patch}) {
    while (pos < text.size() && text[pos] >= '0' && text[pos] <= '9') {
      *part = *part * 10 + static_cast<std::uint64_t>(text[pos] - '0');
      ++pos;
    }
    ++pos;  // the '.' or '-'
  }
  if (pos <= text.size()) {
    v.pre.emplace_back(text.substr(pos - 1));
  }
  return v;
}

std::strong_ordering compare(const Version& a, const Version& b) {
  // TODO: the rules in the header. This compares the pre-release identifiers as strings, which is
  // what MiniDAQ's own Version does and is wrong for "rc.10" against "rc.2".
  return std::tie(a.major, a.minor, a.patch, a.pre) <=> std::tie(b.major, b.minor, b.patch, b.pre);
}

}  // namespace semver
