# Notes on the solution

- **Why `WrongArg` is rejected.** `t.consume(s)` with `s` a `const Single&` has no viable
  overload when the member takes `int`, so the requirement fails. A concept is checked
  with the exact expression you write, so write the call the algorithm will make.
- **`same_as<bool>` vs `convertible_to<bool>`.** For filters the solution demands exactly
  `bool`. `convertible_to<bool>` would accept `int`, pointers and anything with an
  `operator bool`, which hides bugs such as returning a count. For `count()` the looser
  `convertible_to<uint64_t>` is right: any unsigned integer type is fine.
- **const correctness in the concept.** `count()` is required on a `const T&`, and
  `accept()` on a `const F&`, because `feed` calls it on a const object. If your concept
  is weaker than your algorithm's use, the error moves back into the template body.
- **Error messages.** Passing a bad type now fails at the call site with "constraints not
  satisfied ... because 'ct.count()' would be invalid", instead of a deep template error.
- **Concepts vs virtual interfaces.** Concepts give static dispatch: `feed` is instantiated
  per pair of types and the calls inline, which matters at 30 M singles/s. A virtual
  `ISink` gives one compiled `feed` and run-time substitution (useful for plugins and
  test doubles across library boundaries). MiniDAQ uses concepts inside the hot path and
  virtual interfaces at the hardware boundary (Chapter 6).
