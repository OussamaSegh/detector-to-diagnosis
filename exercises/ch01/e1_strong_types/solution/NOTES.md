# Notes on the solution

- The tag type is never instantiated; it only makes `Quantity<PicosecondsTag, int64_t>`
  and `Quantity<KeVTag, float>` different types. That is the whole trick.
- Operators are hidden friends: they are found only by argument-dependent lookup, so they
  never take part in overload resolution for unrelated types, and `Picoseconds + KeV`
  has no viable candidate at all (a clean "no match" error, not an ambiguity).
- `explicit` on the constructor blocks `Picoseconds p = 5;`. There is no conversion
  operator back to `Rep`, so the raw number leaves only through `count()`, which is
  easy to grep for in review.
- Scaling by `Rep` is allowed (a window times 2 is still a window). Dividing two
  quantities of the same unit returns `Rep`, the dimensionless ratio.
- Trade-off: this simple version does not model derived units (keV per ps). MiniDAQ
  never needs them; if you do, look at mp-units (a candidate for C++29) rather than
  growing this by hand.
- Cost: with -O2 the generated code is identical to raw `int64_t` arithmetic. Check it in
  Compiler Explorer with `-O2 -std=c++20`.
