// Exercise F1.4 (audit), starter: the recorded change of CHANGE.md, as it was proposed.
#pragma once

#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "counted.hpp"

namespace ex {

struct Header {
  int run;
  std::string note;
  Header(int r, std::string n) : run{r}, note{std::move(n)} { ++Live::headers(); }
  ~Header() { --Live::headers(); }
  Header(const Header& o) : run{o.run}, note{o.note} { ++Live::headers(); }
  Header& operator=(const Header&) = default;
};

struct Index {
  std::vector<std::uint64_t> offsets;
  std::size_t capacity;
  explicit Index(std::size_t cap) : capacity{cap} {
    if (cap == 0) throw std::invalid_argument{"index capacity must be at least 1"};
    offsets.reserve(cap);
    ++Live::indexes();
  }
  ~Index() { --Live::indexes(); }
  Index(const Index& o) : offsets{o.offsets}, capacity{o.capacity} { ++Live::indexes(); }
  Index& operator=(const Index&) = default;
};

// [snippet:leak]
class RunLog {
 public:
  RunLog(int run, std::string note, std::size_t capacity)
      : header_{new Header{run, std::move(note)}}, index_{new Index{capacity}} {}
  ~RunLog() {
    delete index_;
    delete header_;
  }
  // [/snippet:leak]

  [[nodiscard]] int run() const { return header_->run; }
  [[nodiscard]] const std::string& note() const { return header_->note; }
  bool add_block(std::uint64_t offset) {
    if (index_->offsets.size() == index_->capacity) return false;
    index_->offsets.push_back(offset);
    return true;
  }
  [[nodiscard]] std::size_t blocks() const { return index_->offsets.size(); }

 private:
  Header* header_;
  Index* index_;
};

}  // namespace ex
