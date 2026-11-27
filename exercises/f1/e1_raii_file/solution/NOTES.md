# Notes on the solution

**One owner.** A `File` owns one `FILE*` or nothing. The destructor is the one place that closes
it, so no path through the caller's code can forget: an early `return`, a `break` and an exception
all run the destructor. This is RAII: the resource's lifetime is the object's lifetime.

**No copies.** If two `File` objects held the same `FILE*`, both destructors would call `fclose`
on it, and the second call is undefined behavior. Deleting the copy operations turns that bug into
a compile error.

**Moves with `std::exchange`.** `std::exchange(other.f_, nullptr)` reads the other's pointer and
leaves `nullptr` behind in one expression, so the moved-from object's destructor does nothing.
Move assignment must close what the target owned first, or that file leaks; the `this != &other`
test keeps `f = std::move(f)` from closing the file it is about to keep.

**`noexcept`.** The moves only copy a pointer, so they cannot throw, and saying so lets
`std::vector<File>` move its elements when it grows instead of trying to copy them.

**A factory instead of a throwing constructor.** `File::open` returns `std::optional<File>`: an
open that fails is an ordinary outcome (a missing file), not an exceptional one. Chapter 1 and
Chapter F2 replace the `optional` with `std::expected`, which also says why the open failed.

**In MiniDAQ.** `UdpDetector` (`minidaq/src/control/udp_detector.cpp`) owns its socket the same
way: its destructor closes the descriptor, and it deletes both copies and moves, since it is only
ever held through a `std::unique_ptr`.
