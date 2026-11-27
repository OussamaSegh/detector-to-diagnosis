```{=latex}
\setcounter{chapter}{1}
\renewcommand{\thechapter}{F\arabic{chapter}}
\renewcommand{\theHchapter}{F\arabic{chapter}}
```

# Modern C++, from C++11 to C++23 {#chf2}

::: box-why
C++ changes every three years, and code written to different standards looks like different
languages. A codebase that lives for a decade, as medical device software does, contains all of
them: a loop from 2008 next to a range pipeline from 2022, an error code next to
`std::expected`. You will read and review all of it, and you will decide which features your
team may use, on which compiler. This chapter walks the standards in order, on one running
example, and ends with what your compiler actually supports.
:::

**A day in the life.** A teammate's change replaces a helper with `std::ranges::to`, a C++23
feature, and the build passes on their machine. It fails on the build server with an error that
does not mention C++23 at all: `'to' is not a member of 'std::ranges'`. Both machines compile
with `-std=c++23`. The difference is the standard library: theirs is GCC 14's, the server's GCC
13's, and a standard is a list of features that each library ships over several releases. The
fix is a decision, not a patch: which compiler the project builds with, and what the code does
where a feature is missing. MiniDAQ records that decision in an ADR, and this chapter shows how
to test for a feature in the code itself.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Read code written in each style from C++98 to C++23 and say what each modern feature
   replaces and why.
2. Use move semantics, smart pointers, `auto`, lambdas, structured bindings, `std::optional`,
   `std::variant` and `std::string_view` correctly.
3. Use C++20's concepts, ranges and views, `std::span`, `std::format` and the three-way
   comparison, and explain what coroutines and modules are.
4. Use C++23's `std::expected` and its monadic operations, explicit object parameters,
   `std::ranges::to`, `std::print`, the multidimensional subscript and the small utilities.
5. Find out whether a compiler and its standard library support a feature, and write code that
   adapts with a feature-test macro.

## Prerequisites and estimated time {.unnumbered}

Chapter F1, or the equivalent: classes, RAII, templates, the containers and lambdas. Reading:
about 3 hours. Exercises: 3 to 4 hours. Reading MiniDAQ: 45 minutes.

## The running example, in C++98

### The intuition

Every feature in this chapter was added to make some real code shorter, safer or faster. The
best way to see what a feature is for is to watch it replace the code it was made for. The
running example is the first thing anyone computes from a list-mode file: the energy spectrum,
a histogram of the energies of the singles in a range, and the fraction of them in the 511 keV
photopeak.

### Before 2011

```cpp
// C++98: the spectrum of the singles in [lo, hi) with n bins.
std::vector<int> spectrum(const std::vector<Single>& singles, float lo, float hi, int n) {
  std::vector<int> h(n, 0);
  for (std::vector<Single>::const_iterator it = singles.begin(); it != singles.end(); ++it) {
    if (it->energy_kev >= lo && it->energy_kev < hi) {
      int bin = static_cast<int>((it->energy_kev - lo) / (hi - lo) * n);
      if (bin == n) bin = n - 1;
      ++h[bin];
    }
  }
  return h;  // C++98: may copy the whole vector, unless the compiler elides it
}
```

It works, and it is how most C++ was written for twenty years. Look at what the reader must
check: the iterator type spelled out, the loop bounds, the filter and the bin arithmetic mixed in
one body, and a return that may or may not copy. Each standard since has removed one of these.

## C++11 to C++17: the modern baseline

C++11 was large enough that people speak of "modern C++" as everything since. C++14 and C++17
completed it. These features are now everywhere, and a reviewer expects them.

### Move semantics and smart pointers

Chapter F1 showed moves: an rvalue reference `T&&` binds to a temporary or to an object cast with
`std::move`, and a move constructor steals its resources. The practical consequence is that
returning a vector by value costs nothing: the compiler either constructs the result in the
caller's variable directly (**copy elision**, guaranteed since C++17 for a returned temporary) or
moves it. Output parameters "to avoid the copy" are a C++98 habit; return values.

`std::unique_ptr<T>` is the single owner of a heap object, as small and fast as a raw pointer,
and deletes it in its destructor. `std::make_unique<T>(args...)` (C++14) creates one.
`std::shared_ptr<T>` counts its owners and deletes the object with the last one; the count is
atomic, so copying it costs a contended memory operation, and shared ownership makes it hard to
say when an object dies. MiniDAQ uses `unique_ptr` for owned polymorphic objects (a source, a
sink) and `shared_ptr` only where ownership is really shared, such as a signing key read by
several runs.

### `auto`, range-based `for`, lambdas and uniform initialization

```cpp
// C++11/14: the same spectrum.
std::vector<int> spectrum(const std::vector<Single>& singles, float lo, float hi, int n) {
  std::vector<int> h(n, 0);
  auto bin_of = [=](float e) { return std::min(static_cast<int>((e - lo) / (hi - lo) * n), n - 1); };
  for (const auto& s : singles) {
    if (s.energy_kev >= lo && s.energy_kev < hi) ++h[bin_of(s.energy_kev)];
  }
  return h;  // moved, or elided
}
```

`auto` deduces a variable's type from its initializer; use it where the type is obvious or
unspeakable (a lambda, an iterator), and spell the type where it documents something (a unit, a
width). The range-based `for` loops over any container without an iterator in sight. A lambda
names a piece of logic (`bin_of`) where it is used. Brace initialization (`Single s{1, 2, 3.0F}`)
works for every type and refuses narrowing conversions, such as a `double` into an `int`.

### `constexpr`, `static_assert` and `enum class`

`constexpr` (C++11, greatly extended in C++14 and C++20) marks a function that can run at
compile time when its arguments are constants. `static_assert` checks a condition at compile
time. `enum class` is an enumeration whose values do not convert to `int` by accident and do not
leak their names into the surrounding scope. Chapter 1 builds a lookup table of crystal
positions at compile time with them; MiniDAQ uses `static_assert` to keep `Single` at exactly 16
bytes.

### C++17: structured bindings, `std::optional`, `std::variant`, `std::string_view`

C++17 added the vocabulary types that let an interface say what it means:

```cpp
std::optional<std::size_t> find_crystal(std::span<const Single> s, std::uint32_t crystal);

std::map<std::uint32_t, std::size_t> counts = count_per_crystal(batch);
for (const auto& [crystal, n] : counts) {          // structured bindings: name the parts
  std::printf("%u: %zu\n", crystal, n);
}

if (auto pos = find_crystal(batch, 17); pos) {     // if with an initializer
  use(batch[*pos]);
}
```

`std::variant<A, B, C>` holds exactly one of several types, a type-safe union; `std::visit`
calls the right function for the one it holds (Chapter F6 builds a request handler with it).
`std::string_view` is a pointer and a length into characters someone else owns: a cheap way to
pass text, and, like every view, a way to dangle (Exercise F2.4). `if constexpr` chooses between
two branches at compile time inside a template. **Class template argument deduction** lets you
write `std::vector v{1, 2, 3}` and `std::pair p{3, 4.5}` without the template arguments.

::: box-mistakes
- `std::move` on a `const` object: it cannot move, so it silently copies.
- `return std::move(local);`: it disables copy elision and is never faster.
- `auto x = some_vector[0];` when you meant a reference: `auto` drops references and `const`.
- A `std::string_view` member or return value that points into a temporary string.
:::

## C++20: the second modernization

C++20 is as large a change as C++11. Four of its features change how code is written every day:
concepts, ranges, `std::span` and `std::format`. Two others, coroutines and modules, change how
code can be structured, and are worth knowing even where you do not use them yet.

### Concepts

A template accepts any type until its body fails to compile on it, with an error deep inside the
instantiation. A **concept** names the requirement and checks it at the call:

```cpp
template <typename P>
concept SingleProcessor = requires(P p, const Single& s) {
  { p.process(s) } -> std::same_as<bool>;   // must have process(Single) returning bool
};

template <SingleProcessor P>
std::size_t run(P& p, std::span<const Single> batch) {
  return static_cast<std::size_t>(std::ranges::count_if(batch, [&](const Single& s) { return p.process(s); }));
}
```

Calling `run` with a type that has no `process` member now fails with one line that names
`SingleProcessor`. The standard library defines the common ones: `std::integral`,
`std::floating_point`, `std::invocable`, `std::ranges::range` and dozens more. A short form,
`void f(std::integral auto x)`, constrains an `auto` parameter. Exercise 1.6 of Chapter 1
constrains MiniDAQ's event processors this way.

### Ranges and views

A **range** is anything with a `begin` and an `end`. The `std::ranges` algorithms take the whole
range, so `std::ranges::sort(v)` instead of `std::sort(v.begin(), v.end())`, and they accept a
**projection**, a function applied before the comparison:

```cpp
std::ranges::sort(batch, {}, &Single::time_ps);                  // sort by time
auto top = std::ranges::max_element(batch, {}, &Single::energy_kev);  // highest energy
```

A **view** is a range that computes its elements lazily from another range, without copying it.
Views compose with `|` into a pipeline that reads in the order the data flows:

```{.cpp include="exercises/f2/e1_ranges_spectrum/solution/spectrum.hpp" snippet="spectrum"}
```

Nothing is computed when the pipeline is built; each element flows through `transform`,
`filter` and `transform` as the `for` loop asks for it. The standard views include `filter`,
`transform`, `take`, `drop`, `take_while`, `reverse`, `keys`, `values`, `iota`, `split`,
`join` and, in C++23, `zip`, `enumerate`, `chunk`, `slide` and `stride`.

Views have two traps. A view refers to its source, so a view that outlives its source dangles,
like a `string_view`. And some views keep state in the view object: a `filter_view` caches the
position of its first element the first time you call `begin()`, so iterating a filter view that
is `const`, or changing the elements it filtered on and then iterating it again, does not do what
a reader expects. Build views where you use them, use them once, and do not store them.

### `std::span`

`std::span<T>` is a pointer and a length: a view of any contiguous sequence, whether a vector, an
array, a C array or a part of one. It replaces the pair `(const T* data, std::size_t n)` in every
interface that reads or writes elements without owning them:

```cpp
std::size_t decode(std::span<const std::byte> in, std::span<Single> out);
```

The call site passes a vector, an array or a `subspan`, and the function cannot run past either
end without the compiler-generated bounds being in plain sight. MiniDAQ's interfaces use spans
everywhere data crosses a boundary without changing owner.

### `std::format`, and comparison with `<=>`

`std::format` (C++20; GCC 13) is type-safe formatting with Python-like replacement fields:

```cpp
std::string line = std::format("run {:>6}: {:10.3f} kcps, {} lost", run, rate_kcps, lost);
```

It checks the format string against the arguments at compile time, it cannot overflow a buffer
like `sprintf`, and user types can be made formattable. The **three-way comparison** `<=>`
("spaceship") with `= default` writes all six comparison operators of a class from its members,
in order:

```cpp
struct Version {
  int major, minor, patch;
  friend auto operator<=>(const Version&, const Version&) = default;
};  // Version{2, 3, 0} < Version{3, 0, 0} is true
```

`consteval` (a function that must run at compile time) and `constinit` (a static variable that
must be initialized at compile time) complete C++20's compile-time tools.

### Coroutines: the idea

A **coroutine** is a function that can pause and be resumed later, keeping its local variables in
a frame of its own. A function becomes a coroutine by containing `co_yield`, `co_await` or
`co_return`. C++20 provides only the machinery: you need a library type, such as a generator, to
use it. The form most code uses is a generator: a function that produces a sequence one value at
a time, when the caller asks for the next.

```{.cpp include="exercises/f2/e3_generator/solution/listmode.hpp" snippet="singles"}
```

Each `co_yield` hands one single to the caller's loop and pauses; the next turn of the caller's
loop resumes the function after the `co_yield`. A caller that stops after three singles has
decoded three records, whatever the size of the file. C++23 adds `std::generator<T>` (in
libstdc++ from GCC 14). For GCC 13, Exercise F2.3 ships a small `Generator<T>` with the same
shape; its core is the **promise type** the compiler talks to:

```{.cpp include="exercises/f2/e3_generator/solution/generator.hpp" snippet="promise"}
```

`initial_suspend` returning `std::suspend_always` makes the generator lazy, `yield_value` stores
the value and pauses, and the iterator's `++` resumes the coroutine. You will rarely write a
promise type; it helps to know there is one when a debugger shows you a coroutine frame.
Coroutines also drive asynchronous I/O (`co_await` on a socket), which needs a library such as
Asio; MiniDAQ uses threads and an event loop instead (Chapters F4 and 6).

### Modules: the promise, and why MiniDAQ waits

A **module** replaces the text pasting of `#include` with a compiled interface: `import
minidaq.core;` reads a binary description of what the module exports, once, instead of
re-parsing headers in every translation unit. Modules promise faster builds and no macro leakage
between files. In practice, a modular build needs the compiler, the build system and every
dependency to agree on how module interfaces are built and found. CMake supports C++20 modules
with Ninja since version 3.28, but GCC 13's support is incomplete, and the standard library as a
module (`import std;`) is a C++23 feature that the book's compilers do not provide. ADR 0035
leaves modules out of MiniDAQ for those reasons; revisit it with each change of compiler.

## C++23: finishing C++20

C++23 is a smaller standard that completes what C++20 started. Most of its library features
arrived in GCC 14 or later, so on the book's reference compiler, GCC 13, a part of what follows is
a preview; the last section says exactly which.

### `std::expected` and its monadic operations

`std::expected<T, E>` holds either a value of type `T` or an error of type `E`. It is the return
type of a function that can fail for a reason the caller should handle:

```cpp
enum class ParseError { truncated, negative_time, crystal_out_of_range };

std::expected<Single, ParseError> parse_single(std::span<const std::byte> bytes);

auto r = parse_single(rec);
if (!r) {
  ++errors[std::to_underlying(r.error())];   // count, do not throw
  return;
}
use(*r);
```

The **monadic operations** (`and_then`, `transform`, `or_else`, `transform_error`; GCC 13)
chain steps that can each fail, without an `if` after every step:

```cpp
auto e = parse_single(rec)
             .and_then(check_crystal)                         // another step that can fail
             .transform([](const Single& s) { return s.energy_kev; });  // a step that cannot
```

The first failure short-circuits the rest and its error comes out at the end. `std::optional`
gained the same operations in C++23.

### Explicit object parameters ("deducing `this`")

A member function can name its object as an explicit first parameter, `this Self&& self`. The
classic use removes the duplicated `const` and non-`const` overloads of an accessor:

```cpp
class Run {
 public:
  template <typename Self>
  auto&& singles(this Self&& self) { return std::forward<Self>(self).singles_; }
 private:
  std::vector<Single> singles_;
};  // one function serves const Run&, Run& and Run&&
```

It also lets a lambda call itself recursively, and replaces many uses of the curiously
recurring template pattern (Chapter F6). GCC 14 and Clang 18 support it; GCC 13 does not, which
is why ADR 0035 leaves it out of MiniDAQ.

### `std::print` and `std::ranges::to`

`std::print` and `std::println` (GCC 14) write `std::format` output straight to standard output
or a `FILE*`, with no intermediate string and correct handling of Unicode terminals:

```cpp
std::println("run {}: {} singles, {:.1f}% in the photopeak", run, n, 100.0 * fraction);
```

`std::ranges::to<C>` (GCC 14) collects a range into a container, closing the gap that made every
C++20 pipeline end in a loop or an iterator-pair constructor:

```cpp
auto energies = batch | std::views::filter(in_peak) | std::views::transform(&Single::energy_kev)
                      | std::ranges::to<std::vector>();
```

Exercise F2.1 uses it where the library has it, and falls back where it does not, with the
technique of the last section:

```{.cpp include="exercises/f2/e1_ranges_spectrum/solution/spectrum.hpp" snippet="to"}
```

### `std::mdspan` and the multidimensional subscript

An image or a sinogram is a multidimensional array stored in one flat buffer. C++23 adds the
syntax and the type to index it. A class may now define `operator[]` with several parameters
(GCC 12), so `sino[angle, bin]` is valid C++, and `std::mdspan` is a non-owning view of a flat
buffer as an array of any rank, with a choice of layout:

```cpp
std::vector<float> data(n_angles * n_bins);
std::mdspan sino{data.data(), n_angles, n_bins};   // row-major by default (layout_right)
sino[12, 40] += 1.0F;
```

`std::mdspan` is not in libstdc++ up to GCC 14. Exercise F2.2 writes the two-dimensional case
by hand, which shows that the type is nothing more than a pointer, the extents and an index
formula, and a test compares the two where the library has `<mdspan>`:

```{.cpp include="exercises/f2/e2_sinogram_view/solution/sinogram_view.hpp" snippet="view"}
```

### `std::flat_map` and the small utilities

`std::flat_map<K, V>` (GCC 15) is a sorted map stored in two vectors, one of keys and one of
values. Lookup is a binary search on contiguous memory, much faster than a tree's pointer
chasing for small and medium maps, at the price of linear-time insertion. Chapter F7 measures it
against `std::map`.

The small additions are each a line of code that used to be a helper in every project:

| Feature | What it does |
|-------------------------------|----------------------------------------------------------------|
| `std::to_underlying(e)` | The integer value of an `enum class` value, without a cast that names the type |
| `std::unreachable()` | Tells the compiler a point cannot be reached; reaching it is undefined behavior |
| `std::byteswap(x)` | Reverses the bytes of an integer, for formats in the other byte order |
| `std::move_only_function` | A `std::function` that can hold a move-only callable, such as a lambda owning a `unique_ptr` |
| `if consteval` | Takes one branch when evaluated at compile time, the other at run time |
| `static operator()` | A function object without a `this` pointer, slightly cheaper to call |

`std::unreachable` deserves the warning that ADR 0035 gives it: on a value that comes from
outside the program (a register, a file, a datagram), "this cannot happen" is a belief, and
turning a wrong belief into undefined behavior turns a bad packet into anything at all. Keep a
defined fallback for such values.

::: box-mistakes
- `std::unreachable()` in the `default` of a `switch` over a value read from hardware.
- Ending every `std::expected` chain in `.value()`, which throws on an error and defeats the
  point; handle the error.
- A coroutine that takes a parameter by reference to a temporary: the frame outlives the
  temporary.
- Using a C++23 feature because one compiler accepts it, without checking the project's others.
:::

## What your compiler supports

### Standards ship in pieces

A standard is published once, but compilers and their standard libraries implement it over
several releases, and the compiler (GCC, Clang) and the library (libstdc++, libc++) are separate
projects. Clang on Linux uses GCC's libstdc++ by default, so "Clang 18" supports the *language*
features of Clang 18 and the *library* features of whichever libstdc++ is installed. The table
lists the features of this chapter, with the first release of each that has them, from the
compiler support tables of cppreference at the time of writing, and what the book's reference
setup (Ubuntu 24.04, GCC 13) reports:

| Feature | Standard | First GCC (libstdc++) | First Clang (libc++) | GCC 13 |
|---------------------------------|-------|-----------|------------------|-------|
| `std::format` | C++20 | 13 | libc++ 17 | yes |
| Coroutines (language) | C++20 | 10 | partial | yes |
| Modules | C++20 | partial | partial | partial |
| `std::expected` | C++23 | 12 | libc++ 16 | yes |
| Monadic `std::expected` | C++23 | 13 | libc++ 17 | yes |
| Multidimensional `operator[]` | C++23 | 12 | 15 | yes |
| `if consteval` | C++23 | 12 | 14 | yes |
| `std::to_underlying`, `std::byteswap`, `std::unreachable` | C++23 | 11 to 12 | libc++ 13 to 15 | yes |
| `std::move_only_function` | C++23 | 12 | not yet | yes |
| Explicit object parameters | C++23 | 14 | 18 | no |
| `std::print` | C++23 | 14 | libc++ 18 | no |
| `std::ranges::to` | C++23 | 14 | libc++ 17 | no |
| `std::generator` | C++23 | 14 | not yet | no |
| `std::flat_map` | C++23 | 15 | libc++ 20 | no |
| `std::mdspan` | C++23 | after 14 | libc++ 17 (partial) | no |

The GCC 13 column was checked on the book's machine with the feature-test macros of the next
section, and GCC 14 (the `g++-14` package of Ubuntu 24.04) was checked the same way: it adds
`std::print`, `std::ranges::to`, `std::generator` and explicit object parameters, and still has no
`<mdspan>`. Ubuntu 25.10 makes GCC 15 its default compiler; check the release notes of the
Ubuntu release you build on, and the tables on cppreference, which are updated as compilers
ship.

One combination deserves its own line, because MiniDAQ meets it: **Clang 18 with libstdc++ 13
has no `std::expected`**, although both GCC 13 and Clang 18 "support" it. libstdc++ enables
`<expected>` only when the compiler reports C++20 concepts at the final level
(`__cpp_concepts >= 202002L`), and Clang 18 reports an earlier one. The library's header is
there, and it is empty.

### Feature-test macros

Every feature has a macro, defined by `<version>` (for library features) or by the compiler (for
language features), whose value is the date of the feature's last change. Test the macro, not the
compiler's version number:

```cpp
#include <version>

#if defined(__cpp_lib_expected) && __cpp_lib_expected >= 202202L
#include <expected>
template <typename T, typename E> using Expected = std::expected<T, E>;
#else
// a small implementation with the same interface
#endif
```

The macros for this chapter are `__cpp_lib_format`, `__cpp_lib_expected`,
`__cpp_lib_ranges_to_container`, `__cpp_lib_print`, `__cpp_lib_generator`, `__cpp_lib_mdspan`,
`__cpp_lib_flat_map`, `__cpp_explicit_this_parameter` and `__cpp_multidimensional_subscript`.
A program that prints them takes a minute to write, and it answers "does our compiler have X?"
on the build server, not on your laptop.

### A policy, not a preference

Which features a project uses is a decision with consequences: the oldest compiler you must build
with sets the limit, and every shim you write for a missing feature is code to test and later to
delete. MiniDAQ's ADR 0035 states its rule: C++23 everywhere, and a C++23 feature only where GCC
13 and Clang 18 with libstdc++ 13 both have it and it replaces hand-made code. When the project
moves to a newer compiler (roadmap 3.0.0, Theme N), the ADR is revisited, and the shims and
feature tests are removed in the same change.

::: box-regulated
In regulated software the compiler is part of the toolchain the release was verified with. A
change of compiler or standard library is a change to every binary, recorded and verified like
any other change: the presets, the warnings and the full test suite run on the new compiler
before the first line uses a new feature (Chapters 14 and 32).
:::

## Worked example: the spectrum in C++23

Here is the running example once more, with the features of this chapter where they help and
nowhere else:

```cpp
struct Binning { float lo; float hi; std::size_t bins; };

[[nodiscard]] std::expected<std::vector<std::size_t>, std::string>
spectrum(std::span<const Single> singles, Binning b) {
  if (b.bins == 0 || !(b.lo < b.hi)) return std::unexpected{std::format("bad binning [{}, {})", b.lo, b.hi)};
  const float width = (b.hi - b.lo) / static_cast<float>(b.bins);
  std::vector<std::size_t> h(b.bins, 0);
  for (float e : singles | std::views::transform(&Single::energy_kev)
                         | std::views::filter([b](float e) { return e >= b.lo && e < b.hi; })) {
    ++h[std::min(static_cast<std::size_t>((e - b.lo) / width), b.bins - 1)];
  }
  return h;
}

// The caller:
if (auto h = spectrum(batch, {0.0F, 800.0F, 80})) {
  std::println("{} singles in range", std::ranges::fold_left(*h, std::size_t{0}, std::plus{}));
} else {
  std::println(stderr, "spectrum: {}", h.error());
}
```

Compare it with the C++98 version at the start of the chapter. The input is a span, so a vector,
an array or a part of either can be passed. The binning is a named type, and a bad binning is
reported with its reason instead of dividing by zero. The filter and the bin arithmetic are
separate and named. The result is returned, never copied. Each line uses one feature, and each
feature removes a line a reviewer would otherwise check. (`std::ranges::fold_left` is C++23 too,
in GCC 13.)

## Exercises {.unnumbered}

**Exercise F2.1 (E): The spectrum with ranges and std::ranges::to.** *Goal:* the energies in a
window, an energy histogram and the photopeak fraction, written with views, with a `to_vector`
that uses `std::ranges::to` where the library has it. *Starter:*
`exercises/f2/e1_ranges_spectrum/`. *Acceptance:* `tests/test_spectrum.cpp` checks order, edges,
the empty batch, and agreement with a loop on 20,000 random singles. *Time:* 45 minutes.

**Exercise F2.2 (M): A sinogram view in the shape of std::mdspan.** *Goal:* a non-owning
two-dimensional view with C++23's `v[angle, bin]`, a checked `at`, and `row` as a span.
*Starter:* `exercises/f2/e2_sinogram_view/`. *Acceptance:* `tests/test_sinogram_view.cpp`
checks the row-major layout, writes through the view, bounds, a `const` view, and agreement with
`std::mdspan` where `__cpp_lib_mdspan` is defined. *Time:* 60 minutes.

**Exercise F2.3 (M): A generator over a list-mode file.** *Goal:* rewrite an eager reader and an
eager filter as coroutines that `co_yield` one single at a time. *Starter:*
`exercises/f2/e3_generator/`. *Acceptance:* `tests/test_listmode.cpp` checks that nothing is
decoded before the first request, that three singles cost three decodes, that a filtered stream
pulls only what it needs, and that an exception reaches the caller. *Time:* 60 minutes.

**Exercise F2.4 (A): A view that dangles.** *Goal:* audit a recorded change that returns a
`std::span` and a `std::string_view` "because they do not copy". Write your findings in
`REVIEW.md` and fix the class. *Starter:* `exercises/f2/e4_audit_dangling_view/` (`CHANGE.md`
holds the change). *Acceptance:* `tests/test_spectrum.cpp` checks, by address and without
reading through a dangling view, that the span points into the spectrum, that bounds are
checked, and that the label owns its text. *Time:* 30 minutes.

## Reading MiniDAQ {.unnumbered}

Read these files with the question a reviewer asks of every modern feature: what does it replace,
and does it work on every compiler the project builds with?

1. **`minidaq/include/minidaq/core/expected.hpp`.** Read the comment at the top, then the
   `#if`. On which presets is `minidaq::Expected` an alias of `std::expected`, and on which is
   it the small implementation below? Which test would catch a difference between the two?
   Then read ADR 0035 (`docs/adr/0035-cpp23-baseline.md`) and list the C++23 features it allows
   and the ones it leaves out, with the reason for each. What has to be true of the project's
   compilers before the shim can be deleted?
2. **`minidaq/include/minidaq/core/quantity.hpp` and `byte_io.hpp`.** Both constrain a template
   with a `requires` clause. What does each accept, and what error would a caller see without
   the constraint? Compare them with the event-processor concepts of Exercise 1.6
   (`exercises/ch01/e6_event_concepts/`).
3. **Any decoder in `minidaq/src/format/`.** Find a place that takes a `std::span` of bytes and
   a place that returns `Expected`. Would a monadic chain (`and_then`, `transform`) make one of
   them clearer? Would it make the error path harder to read?

Then read Chapter 1's section "What C++23 adds, and what it replaces", which states the rules the
production code follows.

## Check yourself {.unnumbered}

1. Why is returning a large `std::vector` by value not a performance problem in C++17?
2. When is `std::shared_ptr` the right owner, and what does copying one cost?
3. What does `auto` drop from the type of its initializer, and how do you keep a reference?
4. What does a concept give you that an unconstrained template does not?
5. A `filter_view` is built once and iterated twice, and the elements it filters on change in
   between. What can go wrong?
6. What is the difference between `std::span<const T>` and `const std::vector<T>&` as a
   parameter type?
7. Where is the state of a coroutine kept while it is paused, and what makes a generator lazy?
8. Why does MiniDAQ not use modules?
9. What do `and_then` and `transform` do on a `std::expected` that holds an error?
10. A feature compiles with `-std=c++23` on one machine and not on another. Name two possible
    reasons.
11. Why test `__cpp_lib_expected` instead of the compiler's version number?
12. Why does ADR 0035 forbid `std::unreachable` on a value read from a register?

## Summary {.unnumbered}

- C++11 to C++17 are the modern baseline: move semantics, `unique_ptr`, `auto`, lambdas,
  `constexpr`, structured bindings, `optional`, `variant` and `string_view`. Return values
  instead of output parameters.
- C++20 changes everyday code with concepts, ranges and views, `span` and `format`, and adds
  coroutines and modules as new ways to structure code. A view is lazy, non-owning and can dangle.
- C++23 completes C++20: `expected` with monadic operations, explicit object parameters,
  `print`, `ranges::to`, `mdspan`, `flat_map`, `generator` and small utilities.
- Standards ship in pieces: GCC 13, the book's reference compiler, has `expected` and `format`
  but not `print`, `ranges::to`, `generator` or `mdspan`; Clang 18 with libstdc++ 13 has no
  `expected` at all.
- Test features with the macros of `<version>`, write the shim once, and delete it when the
  project's oldest compiler has the feature. Which features a project uses is a recorded decision.

## Further reading {.unnumbered}

- cppreference, "Compiler support for C++20" and "Compiler support for C++23",
  <https://en.cppreference.com/w/cpp/compiler_support>, and "Feature testing",
  <https://en.cppreference.com/w/cpp/feature_test>.
- The libstdc++ manual, "Implementation Status", <https://gcc.gnu.org/onlinedocs/libstdc++/>,
  and the GCC C++ status page, <https://gcc.gnu.org/projects/cxx-status.html>.
- Scott Meyers, *Effective Modern C++*, O'Reilly, 2014. The C++11 and C++14 features, item by
  item, with their traps.
- Rainer Grimm, *C++20: Get the Details*, Leanpub, 2021. Concepts, ranges, coroutines and
  modules in depth.
- Marius Bancila, *Modern C++ Programming Cookbook*, 3rd edition, Packt, 2024. Short recipes up
  to C++23.
- Lewis Baker, "Coroutine Theory" and the series that follows it,
  <https://lewissbaker.github.io/>. How coroutines work underneath.
