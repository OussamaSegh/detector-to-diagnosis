# Findings (model answer)

| # | Function | UB class | Caught by | Fix |
|---|----------|----------|-----------|-----|
| 1 | `total_duration_saturating` | signed integer overflow | UBSan `signed-integer-overflow` | check `total > max - f` before adding |
| 2 | `fill_energy_histogram` | out-of-bounds write (off by one, `>` instead of `>=`) | ASan `stack-buffer-overflow` (UBSan does not see raw pointer writes) | clamp with `>=` and guard the float conversion |
| 3 | `label_and_extend` | use after free through a dangling reference | ASan `heap-use-after-free` | copy the string before growing the vector |
| 4 | `read_word` | misaligned load and strict-aliasing violation | UBSan `alignment` | `std::memcpy` into a local |
| 5 | `channel_mask` | shift exponent too large for `int` | UBSan `shift-exponent` | shift `std::uint64_t{1}` |

Notes:
- In a Release build without sanitizers tests 1, 3 and 4 usually pass on x86-64, and
  test 2 may pass because the write lands in adjacent stack memory. Passing tests are
  not evidence of correct code when UB is involved.
- The float-to-integer conversion in bug 2 is a sixth, latent UB (`-1.0F` or `1e30F`
  converted to `size_t`); UBSan reports it with `-fsanitize=float-cast-overflow`, which
  is not part of `-fsanitize=undefined` by default in Clang. The solution guards it.
