#pragma once
// Exercise 1.1 starter. TODO: replace these aliases with a strong type.
// Hint: template <typename Tag, typename Rep> class Quantity { ... };
// Keep ex::count(q) working: it must return the underlying number.
#include <cstdint>

namespace ex {

using Picoseconds = std::int64_t;  // TODO: make this a distinct type
using KeV = float;                 // TODO: make this a distinct type

constexpr std::int64_t count(Picoseconds p) { return p; }
constexpr float count(KeV e) { return e; }

}  // namespace ex
