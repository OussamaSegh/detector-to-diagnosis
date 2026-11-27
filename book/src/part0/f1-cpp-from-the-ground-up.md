```{=latex}
\setcounter{chapter}{0}
\renewcommand{\thechapter}{F\arabic{chapter}}
\renewcommand{\theHchapter}{F\arabic{chapter}}
```

# C++ from the ground up {#chf1}

::: box-why
Every later chapter assumes that you can read a C++ class and say who owns each resource, when
each object is destroyed and what happens when an error leaves a function half-way. Those three
questions decide whether code leaks, crashes or silently corrupts data, and the answers are
not in any single line: they follow from a few rules of the language that a reader coming from
Python, Java or C has never needed. This chapter teaches those rules from the beginning, on the
kind of code a data acquisition system is made of.
:::

**A day in the life.** A colleague's change adds a small class that keeps the log of a run: a
header and an index, both allocated with `new` in the constructor and deleted in the destructor.
The tests pass. A week later the acquisition server, which reloads its configuration many times a
day, has grown by a few hundred megabytes. Nobody calls `delete` incorrectly; the leak is in a
line that does not exist. When the index's constructor rejects a capacity of zero by throwing,
the header allocated a moment earlier is never freed, because the destructor of an object whose
constructor did not finish never runs. You will audit that change in Exercise F1.4. By then you
will know why the fix is to write less code, not more.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Explain how a C++ program is built from translation units, what the preprocessor, the
   compiler and the linker each do, and what "undefined reference" and "multiple definition" mean.
2. Say where each object of a program lives (stack, heap, static storage), when it is created and
   destroyed, and the difference between a value, a reference and a pointer.
3. Write a class that owns a resource with RAII, and apply the rule of zero, three and five.
4. Use function and class templates, the main standard containers, iterators, algorithms and
   lambdas, and choose between them.
5. Choose between exceptions, error codes and `std::optional` for a given error, and write code
   that is correct when an exception passes through it.

## Prerequisites and estimated time {.unnumbered}

You can write a loop, a function and a data structure in some programming language, and you
have a Linux machine set up as *How to use this book* describes, with GCC 13, CMake and Ninja.
No C++ beyond "hello, world" is assumed. Reading: about 3 hours. Exercises: 4 to 5 hours.
Reading MiniDAQ: 1 hour.

## The compilation model

### The intuition

Python runs your source file. C++ does not: a C++ program is translated, file by file, into
machine code, and the pieces are then joined into one executable. Most of the error messages a
beginner meets, and many of the design rules of the language, come from that two-step model. If
you know which step produced a message, you know where to look.

### Translation units, the preprocessor and the compiler

A **translation unit** is one `.cpp` file after the preprocessor has run on it. The preprocessor
is a text substitution step. `#include "energy.hpp"` pastes the file's text in place, `#define`
substitutes names, and `#if` keeps or drops lines. The compiler then sees one long file. A
five-line `main.cpp` that includes `<cstdio>` is over a thousand lines after preprocessing
(`g++ -E main.cpp` shows them).

Here is the smallest program with the shape of a real one, three files:

```cpp
// energy.hpp: the declaration, what other files may call
#pragma once
double calibrate(int adc_counts);

// energy.cpp: the definition, the code itself
#include "energy.hpp"
double calibrate(int adc_counts) { return 0.25 * adc_counts + 1.5; }

// main.cpp: a user of it
#include <cstdio>
#include "energy.hpp"
int main() { std::printf("%.1f keV\n", calibrate(2038)); }
```

A **declaration** says that something exists and what its type is. A **definition** is the thing
itself. `main.cpp` needs only the declaration to compile a call to `calibrate`: the compiler
checks the argument type and emits "call the function named `calibrate(int)`", without knowing
where its code is. `#pragma once` keeps a header from being pasted twice into one translation
unit.

Build it by hand, one step at a time:

```text
$ g++ -std=c++23 -c main.cpp       # main.o
$ g++ -std=c++23 -c energy.cpp     # energy.o
$ g++ main.o energy.o -o calib     # link
$ ./calib
511.0 keV
```

### The linker, and its two classic errors

The compiler turns each translation unit into an **object file** (`.o`) with machine code and a
table of symbols: the names it defines and the names it uses but does not define. `nm` lists that
table:

```text
$ nm main.o
                 U _Z9calibratei
0000000000000000 T main
                 U printf
$ nm energy.o
0000000000000000 T _Z9calibratei
```

`T` is a definition in the code section, `U` an undefined name the linker must find elsewhere.
`_Z9calibratei` is `calibrate(int)` after **name mangling**: C++ encodes the parameter types into
the symbol, which is how two overloads `calibrate(int)` and `calibrate(double)` can both exist.
(`nm -C` demangles the names.)

The **linker** joins the object files and resolves each `U` to exactly one `T`. Forget
`energy.o` and it says so:

```text
$ g++ main.o -o calib
/usr/bin/ld: main.o: in function `main':
main.cpp:(.text+0xe): undefined reference to `calibrate(int)'
collect2: error: ld returned 1 exit status
```

An **undefined reference** is never a compiler error. The code compiled; the linker could not
find the definition. The cause is a missing source file or library in the link, a declaration
whose types differ from the definition's (so the mangled names differ), or a function declared
and never written.

The opposite error comes from the **one definition rule** (ODR): a function or a global variable
must be defined exactly once in the whole program. Put a definition in a header, and every
translation unit that includes it defines it again:

```text
$ echo 'double gain() { return 0.25; }' >> energy.hpp
$ g++ main.o energy.o
/usr/bin/ld: energy.o: in function `gain()':
energy.cpp:(.text+0x0): multiple definition of `gain()'; main.o:main.cpp:(.text+0x0): first defined here
```

The fix is `inline double gain()`, which tells the linker that the identical copies are one
definition. Templates, `constexpr` functions and functions defined inside a class body are
implicitly inline; that is why header-only libraries work. A subtler ODR violation, two
*different* definitions of the same inline function or class in two translation units, is not
diagnosed at all: the linker keeps one copy and the program uses it everywhere. Chapter 32 meets
it again with two versions of one library.

```{.dot caption="From source to executable. The preprocessor pastes headers into each .cpp file, the compiler turns each translation unit into an object file with defined (T) and undefined (U) symbols, and the linker resolves every undefined symbol to exactly one definition." width="85%"}
digraph build {
  rankdir=LR; nodesep=0.25; ranksep=0.35;
  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10, fillcolor="#eef3fb", color="#4a6fa5"];
  edge [fontname="Helvetica", fontsize=9];
  h [label="energy.hpp", fillcolor="#fff8e1", color="#b58900"];
  m [label="main.cpp"]; e [label="energy.cpp"];
  pm [label="preprocessed\nmain (1,000+ lines)"]; pe [label="preprocessed\nenergy"];
  om [label="main.o\nT main\nU calibrate(int)"]; oe [label="energy.o\nT calibrate(int)"];
  x [label="calib", fillcolor="#dff0d8", color="#3c763d"];
  h -> pm [style=dashed]; h -> pe [style=dashed];
  m -> pm [label=" cpp"]; e -> pe [label=" cpp"];
  pm -> om [label=" compile"]; pe -> oe [label=" compile"];
  om -> x [label=" link"]; oe -> x;
}
```

### The same program with CMake

Typing the commands does not scale past a few files, and it hides the flags. Every project in
this book is built with CMake, which writes the commands for you from a description of the
targets:

```cmake
cmake_minimum_required(VERSION 3.28)
project(calib LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
add_library(energy energy.cpp)
add_executable(calib main.cpp)
target_link_libraries(calib PRIVATE energy)
```

`cmake -S . -B build -G Ninja` configures and `cmake --build build` builds. A **target** is a
library or an executable; `target_link_libraries` says that `calib` uses `energy`, and CMake puts
the library on the link line. Chapter F3 looks at what the linker does with libraries, and
Chapter 32 at CMake in depth. MiniDAQ's `CMakePresets.json` names the configurations (`debug`,
`release`, `asan-ubsan`, `tsan` and others) so that nobody types the flags.

::: box-mistakes
- Reading the first error of a long compiler message last. Fix the first error first; many of the
  rest follow from it.
- Treating "undefined reference" as a compile error and staring at the call. Look at the link
  line and at the definition's exact types.
- Defining a non-inline function or a global variable in a header.
- `using namespace std;` in a header: it changes the meaning of every file that includes it.
:::

## Values, references and pointers

### The intuition

In Python and Java every variable of a class type is a reference to an object somewhere on the
heap, and a garbage collector frees it later. In C++ a variable *is* the object, by default. It
lives in a definite place, it is destroyed at a definite point, and assigning it copies it. That
one difference, **value semantics**, is the source of C++'s speed and of most beginners'
surprises.

### Objects and their lifetime

Every object has a **storage duration** that says when it is created and destroyed:

- **Automatic** (local variables): created when the definition is reached, destroyed when the
  enclosing block ends, in the reverse order of creation. They live on the **stack**, a region
  the compiler reserves and releases by moving one register, which is why they cost nothing to
  allocate.
- **Dynamic**: created by `new` (or by a container or smart pointer on your behalf), destroyed by
  `delete`. They live on the **heap**, managed by the allocator, at a cost of tens to hundreds of
  nanoseconds per allocation (Chapter 2 measures it).
- **Static**: global variables and `static` locals, created once and destroyed when the program
  ends.

```cpp
void process_run() {
  Single s{.time_ps = 1000, .crystal = 7, .energy_kev = 511.0F};  // automatic: on the stack
  std::vector<Single> batch(4096);   // the vector object is on the stack,
                                     // its 4,096 elements on the heap
  // ...
}  // batch is destroyed: it frees its heap array. Then s is destroyed.
```

The vector shows the pattern that makes C++ manageable: an automatic object that owns heap
memory and frees it in its destructor. You get the heap's flexibility with the stack's
predictable lifetime.

### Built-in types and arithmetic

C++ gives you the machine's own number types, with the machine's own limits:

| Type | Size on x86-64 Linux | Range or precision | Typical use in a DAQ |
|-------------------------------|------------------|----------------------------------|--------------------------------|
| `std::int64_t` | 8 bytes | about ±9.2 × 10^18^ | Timestamps in picoseconds |
| `std::uint32_t` | 4 bytes | 0 to 4,294,967,295 | Crystal ids, hardware counters |
| `std::uint8_t` | 1 byte | 0 to 255 | Raw bytes, small codes |
| `float` | 4 bytes | about 7 significant digits | Energies in keV |
| `double` | 8 bytes | about 16 significant digits | Sums, statistics, calibration |
| `std::size_t` | 8 bytes | 0 to 2^64^ − 1 | Sizes and indices |

Use the fixed-width types of `<cstdint>` whenever a value has a meaning in bits: a field of a
packet, a counter in a register, a record on disk. Plain `int` and `long` have sizes the standard
does not fix.

Three rules of arithmetic surprise every newcomer. **Unsigned arithmetic wraps**: `0u - 1u` is
4,294,967,295, by definition, which is exactly what a hardware counter does and exactly wrong for
a difference that should be negative. **Signed overflow is undefined behavior**: `INT32_MAX + 1`
has no defined result, and the optimizer assumes it never happens. And **mixing signed and
unsigned** converts the signed value to unsigned, so `-1 < 1u` is `false`. MiniDAQ builds with
`-Wconversion -Wsign-conversion` and treats warnings as errors, so the compiler points at every
such mix; the fix is an explicit `static_cast` that says what you meant, or a better type.

Floating point is a different trap: `0.1 + 0.2 == 0.3` is `false`, because neither side is
exactly representable in binary. Compare floating-point results with a tolerance, and never
accumulate many `float` values into a `float` sum: each addition rounds, and a sum of millions of
energies drifts. Accumulate into `double`, as every example in this chapter does.

### Copies, references and `const`

Assignment and parameter passing copy by default:

```cpp
std::vector<Single> a(1000);
std::vector<Single> b = a;   // a second vector with its own 1,000 elements
b[0].crystal = 99;           // a[0] is unchanged
```

A **reference** is another name for an existing object. It must be bound when it is created and
cannot be rebound. Passing by reference avoids the copy, and `const` promises not to change it:

```cpp
double total_energy(const std::vector<Single>& batch);  // no copy, no modification
void   sort_batch(std::vector<Single>& batch);          // no copy, sorts the caller's vector
Single make_single(std::int64_t t);                     // returns a new value
```

Those three signatures carry most of the meaning of a C++ interface: read it, change it, or make
a new one. The rule of thumb: pass small types (up to two machine words, such as `int`,
`double`, a 16-byte `Single`) by value, larger ones by `const&` when you only read them, and by
`&` when the function's purpose is to change them.

### Pointers, and why production code rarely owns through them

A **pointer** is an object that holds an address. It can be null, it can be changed to point
elsewhere, and dereferencing it (`*p`, `p->x`) reaches the object it points at:

```cpp
Single s{};
Single* p = &s;        // p holds the address of s
p->crystal = 12;       // s.crystal is now 12
Single* q = nullptr;   // points at nothing; *q would be undefined behavior
```

A pointer says nothing about **ownership**: whether whoever holds it must `delete` the object,
or must not. `Single* f()` might return a pointer into an array you must not free, or a new
object you must. The compiler cannot tell, so neither can the reviewer. That is why modern C++
uses raw pointers (and references) only to *observe* objects owned by someone else, and owns
through types that say so: a value member, a container, `std::unique_ptr<T>` (one owner) or
`std::shared_ptr<T>` (shared ownership, rarely the right answer). Chapter 1 has the full table.

The worst pointer bug has a name: a **dangling** pointer or reference, which outlives the object
it refers to.

```cpp
const Single& first(const std::vector<Single>& v) { return v.front(); }

const Single& s = first(load_batch());  // the vector returned by load_batch() is destroyed
                                        // at the end of this line; s refers to freed memory
```

Nothing fails at compile time, and the program may even print the right value for a while,
because freed memory is not cleared. This is **undefined behavior**: the language makes no
promise about what happens, and the optimizer is allowed to assume it never occurs. Chapter 1
tours the kinds of undefined behavior and the sanitizers that find them; build your exercises
with the `asan-ubsan` preset and most of them become a clear error report.

## Classes, RAII and the rule of zero

### The intuition

A class bundles data with the functions that keep it valid. Its most important functions are the
ones you do not call: the **constructor**, run when an object is created, and the **destructor**,
run when it is destroyed. Because C++ destroys objects at a definite point, on every path out of
a scope, the destructor is the one place where cleanup cannot be forgotten. Tie a resource (a
file, a socket, a lock, heap memory) to an object's lifetime, and it is released exactly once,
whatever happens. That is **RAII**, "resource acquisition is initialization", and it is the one
idea that makes C++ safe.

### Constructors and destructors

```cpp
class Stopwatch {
 public:
  explicit Stopwatch(std::string name)
      : name_{std::move(name)}, start_{std::chrono::steady_clock::now()} {}
  ~Stopwatch() {
    const auto us = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::steady_clock::now() - start_);
    std::printf("%s: %lld us\n", name_.c_str(), static_cast<long long>(us.count()));
  }
 private:
  std::string name_;
  std::chrono::steady_clock::time_point start_;
};

void decode_file() {
  Stopwatch w{"decode"};
  // ... any return, or any exception, below this line still prints the time
}
```

Three details matter. The **member initializer list** (after the colon) builds the members
directly; assigning them in the body would build them empty first and then overwrite them.
Members are initialized in the order they are *declared* in the class, whatever order the list
names them in, and destroyed in the reverse order. `explicit` stops the compiler from silently
converting a `std::string` into a `Stopwatch` where one is expected.

### RAII for a C resource

C libraries hand out resources as handles that you must release by hand: `std::fopen` returns a
`FILE*` that you must `std::fclose`. Wrapping such a handle is the first RAII class most C++
engineers write, and it is Exercise F1.1:

```{.cpp include="exercises/f1/e1_raii_file/solution/file.hpp" snippet="file"}
```

The destructor closes. The copy operations are **deleted**, because two `File` objects holding
the same `FILE*` would close it twice. The **move** operations transfer the handle and leave the
source empty, so that a `File` can be returned from a function or stored in a vector. And the only
way to get a `File` is `File::open`, which returns an open file or nothing: there is never a
`File` in a half-built state.

### Copy and move, shown with a counting type

What do copies and moves actually do? A type that prints its special member functions shows it:

```cpp
struct Loud {
  Loud() { std::puts("construct"); }
  Loud(const Loud&) { std::puts("copy"); }
  Loud(Loud&&) noexcept { std::puts("move"); }
  ~Loud() { std::puts("destroy"); }
};

std::vector<Loud> v;
v.reserve(2);
Loud a;                      // construct
v.push_back(a);              // copy: a is still needed afterwards
v.push_back(std::move(a));   // move: we promise not to use a's value again
                             // at the end: destroy, destroy, destroy
```

A **move** is a copy that is allowed to steal. For a type that owns heap memory, a copy allocates
and copies every element; a move copies one pointer and leaves the source empty. `std::move` does
not move anything by itself: it is a cast that says "you may steal from this object", and the
move constructor does the stealing. A moved-from object must still be valid (destroying or
assigning it must work), but its value is unspecified unless its class promises one.

### The rule of zero, three and five

The five **special member functions** are the destructor, the copy constructor, the copy
assignment, the move constructor and the move assignment. The compiler writes all of them for
you, and its versions copy, move and destroy each member in turn. Whether that is right depends
on the members:

- **Rule of zero.** If every member manages itself (values, `std::string`, `std::vector`,
  `std::unique_ptr`), declare none of the five. The compiler's versions are correct and
  efficient. This is the default for almost every class.
- **Rule of three.** If a class needs a user-written destructor, it manages a resource by hand,
  and the compiler's copies copy the handle, not the resource: two owners, one double free. It
  needs a user-written copy constructor and copy assignment too (or must delete them).
- **Rule of five.** Since C++11 it also wants the two moves. Declaring a destructor or a copy
  operation suppresses the compiler's moves, so without them every "move" silently copies.

Exercise F1.2 writes all five for a buffer that owns a `new[]` array, and tests them by counting
allocations:

```{.cpp include="exercises/f1/e2_rule_of_five/solution/samples.hpp" snippet="five"}
```

The copy assignment uses **copy and swap**: build a complete copy first, then swap it in. If the
copy throws, the object is unchanged. The moves are `noexcept`, and that matters more than it
looks: `std::vector` moves its elements when it grows only if their move constructor cannot
throw; otherwise it copies them all, to keep its own guarantee that a failed growth leaves the
vector unchanged.

Write the five once to see what they do. Then let the library write them: a class whose members
are a `std::vector<double>` needs none of this code, and has no line in which to forget a member.

### Inheritance and virtual functions

A class can be derived from a base class, inheriting its members, and a **virtual** function
lets code that holds a reference to the base call the derived class's version. This is how C++
expresses "any kind of event source":

```cpp
class Source {
 public:
  virtual ~Source() = default;                  // a base class with virtual functions needs this
  virtual std::size_t read(std::span<std::uint64_t> out) = 0;  // pure virtual: no default
};

class ReplaySource final : public Source {
 public:
  explicit ReplaySource(std::vector<std::uint64_t> words) : words_{std::move(words)} {}
  std::size_t read(std::span<std::uint64_t> out) override {
    const auto n = std::min(out.size(), words_.size() - next_);
    std::copy_n(words_.begin() + static_cast<std::ptrdiff_t>(next_), n, out.begin());
    next_ += n;
    return n;
  }
 private:
  std::vector<std::uint64_t> words_;
  std::size_t next_ = 0;
};

std::unique_ptr<Source> src = std::make_unique<ReplaySource>(recorded_words);
std::size_t n = src->read(buffer);              // calls ReplaySource::read
```

`= 0` makes `Source` abstract: it cannot be created on its own, only derived from. `override`
asks the compiler to check that the function really overrides a virtual one; without it, a typo
in a parameter type silently declares a new function. `final` says that nothing derives from
`ReplaySource`. The **virtual destructor** matters most: deleting a `ReplaySource` through a
`Source*` without it runs only the base destructor, and the vector leaks. (The compiler warns
with `-Wnon-virtual-dtor`, which MiniDAQ turns on.)

A virtual call costs an indirect jump through a table of function pointers, a few nanoseconds,
and stops the compiler from inlining the call. That is nothing per batch and too much per event
in a loop of millions. Chapter F6 compares virtual functions with templates and `std::function`
for the same job, and measures each. And an object of a derived class must be handled through a
reference or a pointer: copying a `ReplaySource` into a `Source` variable, were it allowed, would
**slice** off everything the derived class added. Abstract bases and deleted copies prevent it.

::: box-mistakes
- Writing a destructor "for safety" in a class whose members already clean up. It suppresses the
  implicit moves, and the class silently becomes copy-only.
- A raw owning pointer member with the compiler's copy: a double free on the first copy.
- Calling a virtual function from a constructor or destructor: the derived part does not exist
  yet, or no longer does.
- Forgetting that members are initialized in declaration order, not in the order of the
  initializer list.
:::

## Templates and the standard library

### The intuition

The standard library is the largest part of C++ you will use, and almost all of it is
**templates**: code written once for any type, which the compiler instantiates for each type it
is used with. A `std::vector<Single>` and a `std::vector<double>` are two different classes
generated from one template, each as fast as if written by hand.

### Function and class templates

```cpp
template <typename T>
T clamp_to(T value, T lo, T hi) {
  return value < lo ? lo : (hi < value ? hi : value);
}

double e = clamp_to(612.4, 0.0, 600.0);        // T = double
std::int64_t t = clamp_to<std::int64_t>(5, 0, 3);  // T named explicitly
```

The compiler deduces `T` from the arguments and generates `clamp_to<double>`. A class template
works the same way:

```cpp
template <typename T, std::size_t N>
class History {  // the last N values
 public:
  void add(T v) { values_[next_++ % N] = v; }
  [[nodiscard]] const std::array<T, N>& values() const { return values_; }
 private:
  std::array<T, N> values_{};
  std::size_t next_ = 0;
};

History<float, 64> recent_rates;
```

A template's definition must be visible where it is used, so templates live in headers. Their
error messages are long because the compiler reports the failure inside the instantiation; read
the first "required from here" line to find your call. C++20's **concepts** turn those messages
into one line that names the requirement the type does not meet (Chapters 1 and F2).

### The containers you will use

| Container | What it is | Use it for |
|-------------------------------|-----------------------------------------|-------------------------------------|
| `std::array<T, N>` | N values inline, size fixed at compile time | Small fixed tables, a crystal's neighbors |
| `std::vector<T>` | A growable array on the heap, contiguous | Almost everything: batches, histograms |
| `std::string` | A growable array of `char` | Text, file names |
| `std::unordered_map<K, V>` | A hash table | Lookup by key, counts per crystal |
| `std::map<K, V>` | A sorted tree | Lookup in key order, ranges of keys |
| `std::deque<T>` | Blocks of arrays, cheap at both ends | Rarely; a queue without a size limit |

Start with `std::vector`. Its elements are contiguous, so the processor's caches and prefetcher
work for you, and it beats the "clever" containers at most sizes that occur in practice (Chapter
F7 measures it). Reserve its capacity when you know the size, and remember that growing it moves
the elements: every pointer, reference and iterator into it is then **invalidated**.

### Iterators, algorithms and lambdas

An **iterator** is a generalized pointer into a container: `begin()` points at the first element,
`end()` one past the last. The `<algorithm>` and `<numeric>` headers hold more than a hundred
algorithms written against iterators, and C++20 added versions that take the whole container
(`std::ranges::`). A **lambda** is an unnamed function object written in place, and its
**capture list** says which local variables it may use:

```cpp
float lo = 435.0F, hi = 585.0F;
auto in_window = [lo, hi](const Single& s) { return s.energy_kev >= lo && s.energy_kev <= hi; };
auto n = std::ranges::count_if(batch, in_window);     // how many in the window
std::erase_if(batch, [&](const Single& s) { return !in_window(s); });  // keep only those
```

`[lo, hi]` captures copies; `[&]` captures everything by reference, convenient inside a function
and dangerous in a lambda that outlives the scope (a callback stored for later, a thread). The
loop each algorithm replaces is easy to write and easy to get subtly wrong, while the algorithm's
name says what it does. Exercise F1.3 answers seven questions about a batch of singles this way:

```{.cpp include="exercises/f1/e3_algorithms/solution/singles.hpp" snippet="algorithms"}
```

Note the comparison `time_then_crystal`. Sorting by time alone leaves singles with equal times in
an unspecified order, so two runs on the same data could produce different output. A total order
makes the result reproducible, which is what makes a regression test possible (Chapter 3).

## Errors

### The intuition

A function can fail in three different ways, and C++ has a tool for each. The input may simply
have no answer (the maximum of an empty batch), which is a normal outcome. A request may fail for
a reason the caller must handle (a file that does not exist). Or something may have gone wrong
that the code around the failure cannot handle at all (memory exhausted, a broken invariant).
Mixing them up produces either code that crashes on ordinary inputs or code that ignores real
failures.

### Exceptions

`throw` leaves the current function and every caller in turn until a `catch` handles it. On the
way, the stack is **unwound**: every automatic object in every scope left is destroyed. This is
why RAII and exceptions belong together. Code that holds its resources in objects is correct when
an exception passes through it, without a single `try`:

```cpp
void write_run(const std::string& path, std::span<const Single> singles) {
  auto f = File::open(path, "w");
  if (!f) throw std::runtime_error{"cannot open " + path};
  for (const auto& s : singles) {
    if (!f->write(format(s))) throw std::runtime_error{"write failed: " + path};
  }
}  // on every path, f's destructor closes the file
```

A function that cannot throw says so with `noexcept`: destructors and move operations should,
and the compiler and the library rely on it. If an exception escapes a `noexcept` function, the
program terminates. Exceptions cost nothing on the path where nothing is thrown and a great deal
(microseconds) when something is, which is why Chapter 1 keeps them off the per-event path of an
acquisition.

### Exception safety

When an exception leaves a function, in what state are the objects it touched? There are three
useful promises:

- **No-throw**: the function never throws (destructors, moves, `swap`).
- **Strong**: if it throws, nothing changed (copy and swap gives it).
- **Basic**: if it throws, nothing leaked and every object is still valid, though values may
  have changed.

Every function must give at least the basic guarantee. The leak of this chapter's opening scene
breaks it, and the rule behind it is worth stating exactly: *if a constructor throws, the
destructor of that object does not run, but the members and base classes that were already fully
constructed are destroyed.* A member that is a `std::unique_ptr` or a value cleans up after
itself; a raw pointer member does not.

```{.cpp include="exercises/f1/e4_audit_leak/starter/run_log.hpp" snippet="leak"}
```

When `new Index{0}` throws, `header_` holds the only pointer to the header, and nothing will ever
delete it. The fix, in Exercise F1.4, is to make both members values: a class with no destructor
at all.

### Error codes and `std::optional`

For outcomes the caller must handle, a return value is often clearer than an exception: it is in
the signature, so the caller cannot be unaware of it, and it costs nothing. `std::optional<T>`
holds a `T` or nothing:

```cpp
std::optional<Single> highest_energy(std::span<const Single> s);

if (auto top = highest_energy(batch)) {
  std::printf("highest: %.1f keV\n", top->energy_kev);
}
```

`std::optional` says *that* there is no value but not *why*. When the reason matters, as with a
decoder that can fail in five different ways, C++23's `std::expected<T, E>` holds either the value
or an error of type `E`. Chapter F2 introduces it, and Chapter 1 builds MiniDAQ's error handling on
it. Older interfaces return an error code and write the result through a reference parameter,
or return `bool`; mark such functions `[[nodiscard]]` so that ignoring the result is a warning.

### Where each belongs

| Situation | Tool | Example |
|-------------------------------------|----------------------------|----------------------------------------|
| No value is a normal outcome | `std::optional` | The maximum of an empty batch |
| A failure the caller handles, with a reason | `std::expected` or an error code | Decoding a malformed word |
| A failure nobody nearby can handle | An exception | A configuration file that cannot be read at start-up |
| A bug: something that must never happen | An assertion, then a fix | An index past the end of an array |

An assertion is for the programmer's mistakes, never for bad input: input from a file, a network
or a user is always checked and reported, because it will be wrong one day and the program must
still behave.

::: box-mistakes
- `catch (...) {}`: an error swallowed is an error hidden from the person who must fix it.
- Throwing from a destructor. During unwinding it terminates the program.
- Validating input with `assert`. Release builds remove assertions.
- Returning a sentinel value (`-1`, `0.0`) that is also a valid result.
:::

## Worked example: a batch summary, before and after

To see the pieces together, consider a function that summarizes one batch of singles: how many
fall in the photopeak window, and their mean energy. A first version, as a beginner might write
it:

```cpp
// Version 1: a loop, a raw array and a sentinel.
double summarize(Single* singles, int n, int* in_window) {
  double* energies = new double[n];
  int k = 0;
  for (int i = 0; i <= n; ++i) {                 // reads one past the end
    if (singles[i].energy_kev >= 435 && singles[i].energy_kev <= 585) energies[k++] = singles[i].energy_kev;
  }
  *in_window = k;
  if (k == 0) return -1;                         // -1 is "no data", or is it?
  double sum = 0;
  for (int i = 0; i < k; ++i) sum += energies[i];
  return sum / k;                                // energies is never deleted
}
```

Count the problems: an off-by-one read past the array, a leak on every call, a pointer and a
count that can disagree, an output parameter that may be null, a sentinel that the caller must
know about, and window limits buried in the code. Each one is a line a reviewer must check.

```cpp
// Version 2: the same, written with this chapter's tools.
struct Window { float lo; float hi; };
struct Summary { std::size_t in_window; double mean_kev; };

std::optional<Summary> summarize(std::span<const Single> singles, Window w) {
  auto in = [w](const Single& s) { return s.energy_kev >= w.lo && s.energy_kev <= w.hi; };
  std::size_t n = 0;
  double sum = 0.0;
  for (const auto& s : singles | std::views::filter(in)) {
    ++n;
    sum += s.energy_kev;
  }
  if (n == 0) return std::nullopt;
  return Summary{n, sum / static_cast<double>(n)};
}
```

`std::span` carries the pointer and the length together. The range-based `for` cannot run past
the end. There is no allocation, so nothing to leak. The window is a parameter with a name. The
result says "no data" in its type. The function is shorter and every line has one job. Chapter F2
shows the `std::views::filter` in it, and how C++20 and C++23 make the rest shorter still.

## Exercises {.unnumbered}

**Exercise F1.1 (E): A RAII file handle.** *Goal:* turn a `FILE*` wrapper that relies on callers
to call `close()` into an owner: the destructor closes, copies are deleted, moves transfer and
move assignment closes the old file. *Starter:* `exercises/f1/e1_raii_file/`. *Acceptance:*
`tests/test_file.cpp` checks that no file stays open on any path, including an exception, a move
and a move assignment, and that a failed open opens nothing. *Time:* 45 minutes.

**Exercise F1.2 (M): A rule-of-five buffer with a counting test.** *Goal:* write the four missing
special members of a buffer that owns a `new[]` array: deep copies, stealing moves, copy and
swap, `noexcept` moves. *Starter:* `exercises/f1/e2_rule_of_five/`. *Acceptance:*
`tests/test_samples.cpp` counts allocations: one per copy, none per move, none left at the end,
and a growing `std::vector` moves instead of copying. *Time:* 60 minutes.

**Exercise F1.3 (E): Algorithms instead of loops on singles.** *Goal:* answer seven questions
about a batch of singles, each with the standard algorithm that names it. *Starter:*
`exercises/f1/e3_algorithms/`. *Acceptance:* `tests/test_singles.cpp` checks each function, its
empty case, and agreement with a plain loop on 5,000 random singles. *Time:* 45 minutes.

**Exercise F1.4 (A): A class that leaks on an exception.** *Goal:* audit a recorded change in which
a coding assistant added a run log with two raw owning pointers and said there was no leak. Write
your findings, each with an input that shows it, in `REVIEW.md`, then fix the class.
*Starter:* `exercises/f1/e4_audit_leak/` (`CHANGE.md` holds the specification, the transcript
and the patch). *Acceptance:* `tests/test_run_log.cpp` checks that a capacity of 0 throws and
leaks nothing, and that copies and moves leave no double owner. *Time:* 45 minutes.

## Reading MiniDAQ {.unnumbered}

Open the repository and read three short files with this chapter's questions in mind. You are
reading as a reviewer would: for each type, who owns what, what can fail, and what the compiler
checks for you.

1. **`minidaq/include/minidaq/core/single.hpp`**, the record every stage of the pipeline passes
   on. `Single` has three members and no special member functions at all (rule of zero). Find
   the two `static_assert`s after it. What would break, and where, if someone added a
   `std::string` member? (Hint: the list-mode file writes `Single`s to disk as bytes.) Why is the
   8-byte member declared first?
2. **`minidaq/include/minidaq/core/quantity.hpp`**, a class template `Quantity<Tag, Rep>` that
   gives a number its unit. Which operators does it define, and which does it deliberately leave
   out? Why is its constructor `explicit`? `Picoseconds` and `KeV` in `units.hpp` are two
   instantiations of it: write down what happens at compile time, at the linker and at run time
   when you add a `Picoseconds` to a `KeV`.
3. **`minidaq/include/minidaq/format/raw_single.hpp`** and its `.cpp` in `minidaq/src/format/`.
   `parse_single` takes a `std::span<const std::byte>` and returns `Expected<Single, ParseError>`.
   Which of this chapter's three ways of reporting an error is that, and why not an exception?
   List the `ParseError` values, and say for each whether it is bad input or a bug.

Then read the first section of Chapter 1, "Ownership and lifetime". It starts where this chapter
ends.

## Check yourself {.unnumbered}

1. What does the preprocessor do with `#include`, and what is a translation unit?
2. A program fails with "undefined reference to `calibrate(int)`". Name three possible causes,
   and say which tool's message it is.
3. Why may a template or an `inline` function be defined in a header, but an ordinary function
   may not?
4. Where do the vector object and its elements live in `std::vector<Single> v(100);` inside a
   function, and when is each freed?
5. What is the difference between a reference and a pointer? When would you choose each?
6. State the rule of zero, the rule of three and the rule of five, and say which one a new class
   should normally follow.
7. Why are the move operations of a resource-owning class marked `noexcept`?
8. A constructor allocates two raw arrays with `new`, and the second allocation throws. What
   happens to the first, and why?
9. What does `std::move` do by itself?
10. When does an iterator into a `std::vector` become invalid?
11. A function searches a batch for a crystal and may not find it. Which return type would you
    use, and why not `-1`?
12. Why should input from a network never be validated with `assert`?

## Summary {.unnumbered}

- A C++ program is built in two steps: each `.cpp` file is preprocessed and compiled into an
  object file, and the linker joins them. "Undefined reference" and "multiple definition" are
  linker errors about the one definition rule.
- An object is a value with a definite place and lifetime: automatic objects die at the end of
  their scope, in reverse order. Copies are real copies.
- References and raw pointers observe; values, containers and `std::unique_ptr` own. A reference
  that outlives its object dangles, which is undefined behavior.
- RAII ties each resource to an object's lifetime, so the destructor releases it on every path.
  Follow the rule of zero; write the five only for a class that manages a resource by hand.
- Templates generate type-specific code; the standard containers and algorithms are templates.
  Start with `std::vector` and with the algorithm that names what you do.
- Use `std::optional` when "no value" is normal, `std::expected` or an error code when the caller
  must handle a reason, and exceptions for failures nobody nearby can handle. Every function
  gives at least the basic exception guarantee.

## Further reading {.unnumbered}

- Bjarne Stroustrup, *A Tour of C++*, 3rd edition, Addison-Wesley, 2022. The whole language in
  about 300 pages, by its designer.
- Bjarne Stroustrup, *Programming: Principles and Practice Using C++*, 3rd edition,
  Addison-Wesley, 2024. A full introduction for a reader new to programming in C++.
- The C++ Core Guidelines, <https://isocpp.github.io/CppCoreGuidelines/>, sections C (classes,
  in particular C.20 and C.21 on the special members), R (resource management) and E (errors).
- cppreference, <https://en.cppreference.com>: "Translation phases", "Definitions and ODR",
  "Lifetime", "The rule of three/five/zero", "Exceptions".
- Matt Godbolt, Compiler Explorer, <https://godbolt.org>: paste any example of this chapter and
  read the code the compiler generates.

```{=latex}
\setcounter{chapter}{0}
\renewcommand{\thechapter}{\arabic{chapter}}
\renewcommand{\theHchapter}{\arabic{chapter}}
```
