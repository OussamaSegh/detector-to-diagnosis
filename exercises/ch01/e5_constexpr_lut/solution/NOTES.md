# Notes on the solution

- `consteval` forces compile-time evaluation; `constexpr` only allows it. For a table that
  must exist before `main()` runs, `consteval` is the stronger promise.
- The finished table lives in `.rodata`: 384 x 16 bytes = 6 KiB, no start-up cost, no
  static-initialization-order problems (it is constant-initialized).
- Compile-time evaluation catches UB: an out-of-bounds write in the loop is a compile
  error, not a silent corruption. This is a cheap way to test pure numeric code.
- Limits: compilers cap constexpr evaluation steps (`-fconstexpr-steps` in Clang,
  `-fconstexpr-ops-limit` in GCC). A full 18,432-crystal 3D table with trigonometry fits
  comfortably; a 100 MiB system matrix does not, and should be computed at start-up or
  loaded from a validated file.
- The accuracy of `minidaq::cmath::sincos` (about 1e-15 relative) is far below anything
  that matters for geometry: crystal positions are known to perhaps 10 micrometres.
