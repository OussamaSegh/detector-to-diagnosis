// SPDX-License-Identifier: MIT
#include "group_parser.hpp"

namespace ex21 {
namespace {

struct Parser {
  std::string_view text;
  std::size_t pos = 0;
  ParseResult result;

  // Parses one group; pos is just after its '{'. Returns false on an error. The depth is
  // checked before the recursion: the text decides how deep the stack goes, so the text must
  // not be able to make it deeper than the format allows (MDQ-PR-001 had the same shape).
  bool group(std::size_t depth) {
    if (depth > max_depth) {
      result.error = "groups nested deeper than " + std::to_string(max_depth) + " at byte " +
                     std::to_string(pos - 1);
      return false;
    }
    ++result.groups;
    if (depth > result.depth) {
      result.depth = depth;
    }
    while (pos < text.size()) {
      const char c = text[pos++];
      if (c == '{') {
        if (!group(depth + 1)) {
          return false;
        }
      } else if (c == '}') {
        return true;
      }
    }
    result.error = "group not closed at the end of the text";
    return false;
  }
};

}  // namespace

ParseResult parse_groups(std::string_view text) {
  Parser p;
  p.text = text;
  while (p.pos < text.size()) {
    const char c = text[p.pos++];
    if (c == '{') {
      if (!p.group(1)) {
        return p.result;
      }
    } else if (c == '}') {
      p.result.error = "'}' without '{' at byte " + std::to_string(p.pos - 1);
      return p.result;
    }
  }
  p.result.ok = true;
  return p.result;
}

}  // namespace ex21
