# Notes on the solution

- **Length first.** Every later read is in bounds only because of the first check. In
  review, look for the length check before anything else in a parser.
- **memcpy, not reinterpret_cast.** `*reinterpret_cast<const std::int64_t*>(p)` is UB
  twice over: the byte buffer may be misaligned, and reading bytes through an `int64_t`
  lvalue that was never created breaks the object lifetime rules. `std::memcpy` into a
  local is well-defined, and compilers turn it into a single load.
- **NaN before range.** `nan < 0.0f` and `nan > 2000.0f` are both false, so a range
  check alone silently accepts NaN. Checking `std::isfinite` first closes that hole. The
  test includes NaN and -inf for this reason.
- **Errors are values.** The return type tells the caller that parsing can fail and the
  compiler (with `[[nodiscard]]` on the library version) warns if the result is ignored.
  No exception can escape: the function is `noexcept`.
- **The fuzz loop** is a cheap stand-in for libFuzzer (Chapter 7). Copying each input
  into an exactly-sized `std::vector` matters: on a 16-byte stack array, an over-read of
  the 15-byte prefix would still be inside the array and ASan would not see it.
- **What is not validated here:** time monotonicity and plausibility belong to the
  stream layer (Chapter 9), not to the record parser, which sees one record at a time.
