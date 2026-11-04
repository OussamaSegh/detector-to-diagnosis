# Exercise 32.3: notes

The geometry needs two numbers from the configuration, not the configuration. The solution keeps
those two as members, declares `struct Config;` in `geometry.hpp`, and moves the constructor, the
only code that reads a `Config`, into `geometry.cpp`, which includes `config.hpp`. A source that
includes `geometry.hpp` no longer includes `config.hpp`, so it no longer depends on it.

A forward declaration alone would not do here: the starter's member `Config config_` needs the
complete type, because the size of a `Geometry` depends on it. Keeping a pointer to the
configuration would compile with the declaration but would tie the geometry to the lifetime of
an object it does not own.

By hand:

1. The compiler writes the list: Ninja runs it with `-MD -MF` (CMake adds them), the compiler
   writes every header it opened into a depfile, and Ninja moves those lists into its `.ninja_deps`
   log after each compile. A header is a dependency because the compiler opened it, not because a
   CMake file names it.
2. See the measurements: the time scales with the number of sources that include the header.
3. When the header needs the type's size or members: a member or a base class of that type, an
   inline function that uses its members, a `sizeof`, or a template that instantiates with it.
