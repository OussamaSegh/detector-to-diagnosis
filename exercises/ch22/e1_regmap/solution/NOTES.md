# Exercise 22.1: notes on the solution

**What the generator checks.** The mistakes it refuses are the ones that happen when a map is
edited by hand: an address copied and not changed, a field widened into its neighbor, a new bit in
the reset value that no field describes. Each is cheap to check once, in the specification, and
expensive to find on a board.

**What constants let through.** With constants, `CONTROL_ADDR` and `STATUS_ADDR` are both
`std::uint32_t`, and so are every mask and shift. Nothing stops code from writing to `STATUS_ADDR`
(a read-only register), from using `STATUS_COUNT_MASK` on the value of `CONTROL`, or from a
read-modify-write of a write-1-to-clear register, which clears every flag that was set. With a
type per register and a nested type per field (`tools/regmap_gen.py` and
`minidaq/hw/register.hpp`), a field knows its register, an access knows the register's access, and
all three mistakes are compile errors. The constants are what most C code has; the types cost
nothing at run time and turn a class of defects into build failures.

**Hexadecimal in upper case with fixed widths.** Generated files are read in diffs. Fixed widths
and one case make a changed bit visible in review.
