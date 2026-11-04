# Exercise 32.3 (M): A header that costs a rebuild

**Goal.** Make a change to `config.hpp` recompile only the three sources that use the
configuration, not all eleven.

**Time.** 30 minutes.

**Starter.** `starter/src/geometry.hpp` includes `config.hpp` and keeps a copy of the
configuration, so every source that uses the geometry (the eight `ring_*.cpp`) depends on
`config.hpp`, and so does every rebuild after it changes.

**Acceptance** (`tests/test_rebuild.py`, which builds the project with Ninja and asks Ninja what
it would compile):
- The program prints the sum of the rings, 6143.858.
- After `config.hpp` changes, Ninja compiles `config.cpp`, `geometry.cpp` and `main.cpp`, no other.
- After `geometry.hpp` changes, it still compiles the eight rings.

**Then, by hand.**
1. Run `ninja -C build -t deps build/CMakeFiles/rings.dir/src/ring_0.cpp.o` (the path of the object
   may differ) before and after your change. Where does Ninja get this list?
2. The chapter measures a header that 39 sources include in MiniDAQ (`measurements/ch32/`). How
   long does its rebuild take, and how long a rebuild after changing one leaf source?
3. When is a forward declaration not enough?

**Hints.** A class used only by reference or pointer in a header can be declared there
(`struct Config;`) and defined where it is used.
