# C++20/23 essentials for production code {#ch01}

::: box-why
A DAQ team needs production C++ that is also fast and low-latency, and the first half of that
is easy to underrate. NeuroLF is a medical device with a service life of ten
years or more, and the DAQ software you lead will be read, changed, re-verified and
audited long after you wrote it. Production C++ means code whose ownership, error paths
and failure modes are obvious to the next engineer and provable to an auditor. This
chapter sets the language baseline every later chapter relies on.
:::

**A day in the life.** It is 8:40 on a Tuesday. A clinical site reports that a 40-minute
amyloid scan produced an image with a faint band artifact. The service engineer sends you
the acquisition log. Coincidence counts look normal for 35 minutes, then the reported
singles rate for one detector block jumps to 4.29 billion counts per second and stays
there. You recognize the number: 4,294,967,295 is `UINT32_MAX`. Somebody computed a rate
as `uint32_t current - uint32_t previous` after a counter reset, and the subtraction
wrapped. The image reconstruction trusted the rate for its dead-time correction. Nothing
crashed, every test passed, and a patient image was quietly wrong.

This chapter is about writing code where that class of mistake is hard to make: types that
carry their units, errors that cannot be ignored, ownership that cannot leak or dangle,
and tools that catch undefined behavior before it reaches a scanner.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Use value semantics, RAII and the Rule of 0/5 correctly in every class you write, and
   explain in a review why a given class needs (or must not have) a user-written destructor.
2. Choose between `std::span`, `std::string_view`, references and owning types at an API
   boundary, and state the lifetime contract each choice implies.
3. Use concepts, `constexpr`/`consteval`, ranges and `std::expected` to make interfaces
   that reject misuse at compile time.
4. Name the main classes of undefined behavior (lifetime, bounds, aliasing and alignment,
   arithmetic overflow and invalid shifts, data races) and the tool that catches each.
5. Set up a CMake project where every target builds with `-Wall -Wextra -Wpedantic -Werror`
   on GCC and Clang and runs its tests under AddressSanitizer and UndefinedBehaviorSanitizer.

## Prerequisites and estimated time {.unnumbered}

You should be comfortable with C++17: classes, templates, `std::unique_ptr`, lambdas and
the standard containers. You need a Linux machine (Ubuntu 24.04 or WSL2) with GCC 13,
Clang 18, CMake 3.28 and Ninja; the repository README lists the one-line install.

Reading time is about 3 hours. The exercises take 5 to 6 hours and the MiniDAQ milestone
about 2 hours. In the 10-week schedule this chapter belongs to week 1, together with
Chapters 2 and 8.

## Ownership and lifetime

### The intuition

Every object in a C++ program has exactly one owner that decides when it dies. In a DAQ
that sentence is not philosophy, it is the difference between a pipeline that runs for
eight hours and one that corrupts memory after forty minutes. Buffers of singles travel
from the network receiver to the decoder, the sorter and the writer. At every hand-off
somebody must know whether they now own the buffer (and must free or recycle it) or are
only looking at it (and must not keep the pointer after the call returns).

C++ gives you a tool for each of those two roles:

- **Owning types** manage a resource and release it in their destructor: `std::vector`,
  `std::string`, `std::unique_ptr`, `std::shared_ptr`, a file handle class, a lock guard.
  This is [RAII]{.idx key="RAII (resource acquisition is initialization)"} (resource
  acquisition is initialization): the lifetime of the resource is tied to the lifetime of
  an object, and the compiler guarantees the destructor runs on every exit path,
  including early returns and exceptions.
- **Non-owning views** refer to data someone else owns: raw references, raw pointers
  used as "maybe a reference", `std::span<T>`, `std::string_view`. They are cheap to copy
  (a pointer and a length) and they never free anything.

The engineering rule that follows is short. **Owning types live in data members and in
local variables. Views travel through function parameters.** A function that takes
`std::span<const Single>` promises to look at the singles during the call and forget them
afterwards. A function that takes `std::vector<Single>` by value, or
`std::unique_ptr<Buffer>`, takes ownership. If you can tell which one a function does by
reading its signature, the API is well designed.

### Value semantics and the Rule of 0

The default in modern C++ is [value semantics]{.idx}: copying an object produces an
independent object, assignment replaces the old value, and the object owns all its parts.
`std::vector<Single> a = b;` gives you two vectors that you can change independently.
Value types compose well, are easy to test and cannot be shared by accident across
threads, which is why the C++ Core Guidelines recommend them as the default.

You get correct value semantics without writing a single special member function if all
your data members already have them. That is the **Rule of 0** (Core Guidelines C.20):

> If you can avoid defining default operations, do.

```cpp
// Rule of 0: no destructor, no copy or move operations declared.
class RunSummary {
 public:
  void add(const Single& s) { energies_.push_back(s.energy); }
 private:
  std::string run_id_;
  std::vector<KeV> energies_;
};
```

The compiler generates copy construction, copy assignment, move construction, move
assignment and the destructor, and each one does the right thing member by member.

The **Rule of 5** applies when a class directly manages a resource that has no RAII
wrapper yet: a file descriptor, an `mmap`ed region, a DMA buffer handed out by a driver.
If you write any of the destructor, copy constructor, copy assignment, move constructor
or move assignment, you almost certainly need to think about all five. The classic bug
(and the one in Exercise 1.2) is a class with a destructor that frees memory but
compiler-generated copy operations that copy the pointer: two objects, one allocation,
two `delete[]` calls.

The robust pattern is to write one tiny class per raw resource that follows the Rule of 5
(or, more often, is move-only), and to build everything else from those wrappers with the
Rule of 0. MiniDAQ's later `FileDescriptor` and `MappedRegion` classes (Chapters 12 and
22) are exactly such wrappers.

### Move semantics in one page

A move transfers the resources of an object instead of copying them. After
`auto b = std::move(a);` the vector `b` owns the heap block that `a` had, and `a` is left
in a "valid but unspecified" state: you can destroy it or assign to it, but you should not
assume it is empty unless the type documents that (for `std::unique_ptr` it is
guaranteed null; for `std::vector` it is empty in every real implementation but not
promised by the standard).

Three practical rules cover almost every case:

1. Mark move operations `noexcept`. `std::vector` relocates its elements during
   growth with move construction only if that move cannot throw; otherwise it copies them
   to keep its strong exception guarantee. A missing `noexcept` can silently turn a cheap
   reallocation of a vector of buffers into a deep copy of every buffer.
2. Do not `std::move` a local variable in a `return` statement. `return local;` already
   moves (or elides entirely); `return std::move(local);` prevents copy elision.
3. A function parameter that the function will store is best taken by value and moved
   into place: `void set_name(std::string n) { name_ = std::move(n); }`. Callers with a
   temporary pay one move; callers with an lvalue pay one copy, which they would have
   paid anyway.

### Smart pointers: which one and when

| Need | Use | Cost |
|---|---|---|
| One owner, heap object | `std::unique_ptr<T>` | same as a raw pointer |
| One owner, heap array | `std::unique_ptr<T[]>` or `std::vector<T>` | same as a raw pointer |
| Shared ownership across threads or modules with unclear lifetimes | `std::shared_ptr<T>` | atomic reference count on copy, control block |
| Observe something that may die | `std::weak_ptr<T>` | as `shared_ptr` |
| Observe something that outlives you | `T&`, `T*`, `std::span`, `std::string_view` | free |

In a DAQ hot path, `std::shared_ptr` deserves suspicion. Copying one performs an atomic
increment, and destroying one an atomic decrement, both on a cache line that every
thread holding the pointer touches. At tens of millions of events per second those
atomics show up in profiles. Chapter 3 passes buffers between pipeline stages with
`std::unique_ptr` (single ownership that moves down the pipeline) or by index into a
pre-allocated pool, not with `shared_ptr`.

### Views and how they dangle

`std::string_view` and `std::span` are the most useful additions to C++ interfaces since
C++11 and the most common new source of lifetime bugs. A view is a pointer and a length
into storage somebody else owns. It dangles when that storage dies or moves.

```cpp
std::string_view crystal_label(CrystalId id) {
  std::string s = "crystal-" + std::to_string(id.value());
  return s;  // BUG: the view outlives s
}

std::string_view v = std::string("tmp");   // BUG: temporary dies at the semicolon
std::span<const Single> sp = make_vector(); // BUG: same, with a vector
```

And the subtle one, from Exercise 1.4:

```cpp
const std::string& first = names.front();
names.push_back("x");  // may reallocate; `first` now refers to freed memory
```

How experts avoid these:

- **Never return a view to a local or to a temporary.** Return an owning type instead.
- **Never store a view in a data member** unless the class is explicitly a view itself
  (and documents the lifetime of what it views). A `struct Config { std::string_view
  path; }` is a dangling pointer waiting for a refactoring.
- **Do not hold a view, reference or iterator into a container across an operation that
  may reallocate it** (`push_back`, `insert`, `resize`, `reserve`).
- **Compile with lifetime warnings.** GCC 13 warns about some dangling references
  (`-Wdangling-reference`, enabled by `-Wall` in GCC 13 and later); Clang has
  `-Wdangling` and `-Wreturn-stack-address`. They catch the simple cases, not the
  container case.
- **Run tests under AddressSanitizer**, which reports `stack-use-after-return` and
  `heap-use-after-free` at the exact line. The container case is invisible to the
  compiler but obvious to ASan.

::: box-mistakes
- Writing a destructor "for safety" in a class whose members already clean up. It
  suppresses the implicit move operations, so the class silently becomes copy-only.
- Using `std::shared_ptr` because the ownership is unclear. Shared ownership does not fix
  unclear ownership; it hides it until shutdown order goes wrong.
- Returning `std::string_view` from a function that builds a string.
- Forgetting `noexcept` on a move constructor of a type stored in a `std::vector`.
:::

## Type design: let the compiler check your units

### The intuition

A timestamp in picoseconds, an energy in keV and a crystal number are all "just numbers"
to the CPU. To the physics they are three different things, and mixing them is a bug the
compiler could catch for free if the types said so. Most real DAQ codebases have, at some
point, added a time in nanoseconds to a time in clock ticks. Strong types make that a
compile error.

### A zero-cost Quantity

MiniDAQ's time and energy types are instances of one small template. The tag type is
never instantiated; it only makes `Quantity<PicosecondsTag, int64_t>` and
`Quantity<KeVTag, float>` different types.

```{.cpp include="minidaq/include/minidaq/core/quantity.hpp"}
```

The design decisions are worth reading slowly, because each one closes a class of bugs:

- **The constructor is `explicit`.** `Picoseconds t = 4000;` does not compile; you write
  `Picoseconds{4000}` or, better, `4_ns`. Every place a raw number becomes a time is
  visible in the code and easy to review.
- **There is no conversion back to `Rep`.** The only way out is `count()`, which is
  greppable.
- **Arithmetic is defined only between the same unit**, plus scaling by a plain number.
  `Picoseconds + KeV` finds no operator and fails to compile. The operators are hidden
  friends, so they do not pollute overload resolution for other types.
- **The ratio of two times is a plain number** (`window / tick`), which is what you want
  for "how many ticks fit in the window".
- **Comparisons are defaulted** with `operator<=>`, so `<`, `<=`, `==` and friends all
  exist and agree with each other.

The units header defines the concrete types and user-defined literals:

```{.cpp include="minidaq/include/minidaq/core/units.hpp"}
```

Two choices here deserve a justification, because a reviewer will ask.

*Why integer picoseconds and not `double` seconds?* A `double` has a 53-bit mantissa. Once
a time in picoseconds exceeds $2^{53}$ ps (about 2.5 hours), adjacent `double` values are
more than 1 ps apart and differences between nearby timestamps start to lose precision.
Coincidence sorting subtracts timestamps that are nanoseconds apart from absolute times
that are hours long; that is exactly the operation floating point does badly. A signed
64-bit integer of picoseconds covers about 106 days with exact arithmetic, and signed
differences are natural for "which came first".

*Why `float` for energy?* Energy resolution of a LYSO/SiPM detector is around 10% at 511
keV (about 50 keV FWHM); a `float` resolves differences of about 0.00003 keV at that
scale. Using `float` keeps a `Single` at 16 bytes, four per 64-byte cache line, which
Chapter 2 shows matters more than you might think.

Ids are not quantities, so they get a separate, poorer type: equality, ordering and
hashing, and nothing else.

```{.cpp include="minidaq/include/minidaq/core/ids.hpp"}
```

Finally, the two record types that flow through the whole pipeline:

```{.cpp include="minidaq/include/minidaq/core/single.hpp"}
```

The `static_assert`s are not decoration. They turn assumptions that later code depends on
(16-byte singles, trivially copyable so they can be `memcpy`ed into network buffers and
files) into compile errors the moment someone adds a field.

### enum class and [[nodiscard]]

`enum class` gives scoped, strongly typed enumerations that do not convert to `int`
implicitly. Always give them an explicit underlying type when they appear in a data
structure or a file format (`enum class CoincidenceKind : std::uint8_t`), so their size
does not depend on the compiler.

`[[nodiscard]]` asks the compiler to warn when a return value is ignored. It is most
valuable in two places: on functions whose only effect is their return value (`count()`,
`parse_single()`) and on error types. If you put `[[nodiscard]]` on a *type*, every
function returning that type inherits the warning:

```cpp
enum class [[nodiscard]] WriteStatus : std::uint8_t { ok, disk_full, io_error };
WriteStatus write_block(...);
write_block(...);  // warning: ignoring return value of type 'WriteStatus'
```

With `-Werror`, an ignored error is now a build failure. In a regulated codebase that
turns "the engineer forgot to check the return code" from a code review finding into
something the build server rejects.

### Worked example: the cost of a strong type

Is the wrapper really free? Compile this with `-O2` on GCC 13 or Clang 18 (Compiler
Explorer, <https://godbolt.org>, is the fastest way):

```cpp
#include "minidaq/core/units.hpp"
minidaq::Picoseconds add(minidaq::Picoseconds a, minidaq::Picoseconds b) { return a + b; }
std::int64_t add_raw(std::int64_t a, std::int64_t b) { return a + b; }
```

Both functions compile to the same two instructions on x86-64
(`lea rax, [rdi+rsi]` and `ret`). The wrapper is passed in a register exactly like the
raw integer, because it is a trivially copyable class with a single 8-byte member. The
abstraction exists only in the type checker.

::: box-mistakes
- Adding an implicit conversion operator "for convenience". It re-opens every hole the
  strong type closed.
- Strong-typing ids with arithmetic. Crystal 7 plus crystal 9 is not crystal 16.
- Using `double` seconds for detector timestamps.
- Forgetting the underlying type of an `enum class` that is written to disk.
:::

## Error handling in real-time code

### The intuition

A DAQ sees bad input all the time: a corrupted UDP packet, a word with an impossible
crystal id, a disk that fills up, a control client that sends nonsense. How the code
reports those errors decides whether the hot path stays fast and predictable, and whether
the caller can forget to handle them.

C++ offers four mechanisms. They are not competitors; each has a place.

| Mechanism | Good for | Avoid for |
|---|---|---|
| Exceptions | Configuration, start-up, control-plane errors that abort an operation | Per-event errors on the hot path; code that must have bounded latency |
| `std::expected<T, E>` | Expected failures in data processing (parse errors, validation) | Programming errors that should never happen |
| Error codes / status enums | C APIs, very hot loops, cross-language boundaries | Places where the caller can silently ignore them (add `[[nodiscard]]`) |
| Assertions / contracts | Programming errors: violated preconditions and invariants | Validating external input |

### Why exceptions stay off the hot path

Modern compilers implement exceptions with the "zero-cost" table-based model: a `try`
block costs nothing at run time while no exception is thrown. The problem is the throw.
Throwing allocates the exception object (usually on the heap), walks unwind tables and
runs destructors through every frame; on typical hardware a single throw and catch costs
on the order of a microsecond or more, and the cost varies with stack depth and with
contention on the unwinder's global lock in some runtimes. At 30 million singles per
second you have about 33 ns per single. If one malformed packet in a thousand throws,
exceptions would dominate the CPU budget and, worse, make latency unpredictable.

There are two further, quieter costs. Code that can throw constrains the optimizer
(every call is a potential exit), and exception paths are hard to test exhaustively. That
is why many real-time codebases (games, trading systems, much embedded and automotive
software) compile performance-critical modules with `-fno-exceptions` or forbid throwing
in them by coding rule.

MiniDAQ's rule is the middle ground most medical-device teams use: **exceptions are
allowed in start-up and control code** (parsing a configuration file, opening a socket)
where a failure aborts an operation that a human started; **the per-event data path
never throws** and reports per-event problems through return values and counters.

### std::expected and MiniDAQ's shim

`std::expected<T, E>` (C++23) holds either a value of type `T` or an error of type `E`.
The caller must look at it to get the value, and the error type documents exactly which
failures can happen. It is the right default for "this can fail for reasons outside the
program's control".

There is a practical snag that you will meet in real projects. `std::expected` is a
C++23 library feature. GCC 13 with `-std=c++23` provides it. Clang 17 and 18 used with
the GNU standard library (libstdc++ 13), which is the default on Ubuntu, do not: the
libstdc++ header is guarded on a concepts feature-test macro that those Clang versions do
not yet define. MiniDAQ builds in C++20 on both compilers, so it ships a small
`minidaq::Expected` that becomes an alias of `std::expected` when the standard library
provides it. This is the kind of portability decision you should record in an
architecture decision record (Chapter 6), because a future toolchain upgrade can delete
the shim.

```{.cpp include="minidaq/include/minidaq/core/expected.hpp" lines="1-24"}
```

The parser that the rest of the pipeline uses for MiniDAQ's 16-byte debug record shows
the pattern in full. It never throws, never allocates and never reads outside the span it
is given:

```{.cpp include="minidaq/src/format/raw_single.cpp" snippet="parse"}
```

The function is `noexcept`, so a reviewer knows immediately it cannot surprise the hot
path. Every error has a name. `std::memcpy` reads the fields without alignment or
aliasing undefined behavior (more on that below). The non-finite check comes before the
range check because every comparison with NaN is false: `nan < 0.0f || nan > 2000.0f`
is false, so a range check alone would accept NaN.

Callers then decide what an error means. The decoder in Chapter 9 counts parse errors per
board and per error kind and keeps going; a test asserts on the exact error; a command
line tool prints `to_string(e)` and exits.

### Counting errors instead of logging them

In a DAQ, the most useful error handling is often a counter. A per-board, per-error-type
counter that the control API exposes (Chapter 6) is cheap (one increment), lock-free if
each stage owns its counters, and turns "something odd happened" into a number that a
risk control can check (Chapter 15: an acquisition with any silent drop must be flagged).
Logging every bad event is the opposite: a burst of corrupted packets would turn into a
burst of log lines that blocks the hot thread on I/O.

### Contracts and assertions

Errors in *input* are expected and handled. Errors in *the program* (a function called
with a precondition violated, an invariant broken) are bugs, and the right response is to
stop and make noise during development and testing. C++26 adds contract assertions
(`pre`, `post` and `contract_assert`, from proposal P2900) with configurable evaluation
semantics. Until your toolchain supports them, use `assert` for cheap internal checks in
debug and test builds, and an always-on check that terminates with a clear message for
invariants whose violation would corrupt data. A sorter that receives singles out of time
order, for example, must not silently produce coincidences; in MiniDAQ it raises a fault
in the acquisition state machine (Chapter 6).

::: box-mistakes
- Throwing on malformed input in the per-event path.
- Returning `bool` for "it failed" and losing the reason.
- Logging per event. Count instead, and log the counters periodically.
- Using assertions to validate data from the network: they disappear in release builds.
:::

## Templates and concepts: constraining generic event processors

### The intuition

MiniDAQ processes the same events through different stages: an energy filter, a crystal
filter, a histogrammer, a writer. Templates let you write `feed(events, filter, sink)` once
and have the compiler generate a specialized, fully inlined loop for each combination.
Before C++20, the price was error messages pages long when somebody passed the wrong
type. [Concepts]{.idx} fix that by stating, in code, what a template requires.

### Writing a concept

A concept is a named compile-time predicate on types. The `requires` expression lists
expressions that must compile, and optionally the types they must return:

```cpp
template <typename T>
concept SingleSink = requires(T& t, const T& ct, const Single& s) {
  t.consume(s);                                         // must be callable
  { ct.count() } -> std::convertible_to<std::uint64_t>; // and return a count
};

template <typename T>
concept SingleFilter = requires(const T& f, const Single& s) {
  { f.accept(s) } -> std::same_as<bool>;
};

template <SingleFilter F, SingleSink S>
std::uint64_t feed(std::span<const Single> in, const F& filter, S& sink);
```

Three habits make concepts work for you:

1. **Write the exact expression the algorithm uses.** If `feed` calls `accept` on a
   `const F&`, the concept must require it on a `const F&`. A weaker concept moves the
   error back into the template body.
2. **Prefer `std::same_as<bool>` for predicates** over `std::convertible_to<bool>`, which
   accepts integers and pointers. Returning a count from a filter by mistake should not
   compile.
3. **Use concepts for static polymorphism in hot code and virtual interfaces at
   boundaries.** A concept-constrained template is instantiated per type and inlined; a
   virtual call costs an indirect branch per event and blocks inlining, but lets you swap
   implementations at run time. MiniDAQ uses virtual interfaces where hardware meets
   software (a real network receiver vs a replay file, Chapter 6) and concepts inside the
   per-event loops.

### Ranges, briefly

C++20 ranges compose lazy views over sequences:

```cpp
auto good = singles
          | std::views::filter([](const Single& s) { return s.energy >= 350.0_keV; })
          | std::views::transform([](const Single& s) { return s.crystal; });
```

Ranges are excellent for clarity in analysis code, tests and tools. In the hot path,
measure before you use them: most simple pipelines compile to the same loop as a
hand-written one, but some adaptor combinations (`filter` followed by `reverse`, views
that cache `begin()`) do not, and debug builds of range pipelines are much slower than
plain loops. Chapter 5 shows how to check.

::: box-mistakes
- Concepts that check something different from what the template does.
- `requires` clauses that only check `typename T::value_type` exists, not the operations.
- Virtual dispatch per event in the inner loop "for flexibility" nobody uses.
:::

## Compile-time work: constexpr lookup tables

### The intuition

Some facts about the scanner never change while the program runs: how many crystals there
are, which block a crystal belongs to, where each crystal sits on the ring. If the
compiler computes them, they cost nothing at run time, cannot be computed wrongly by a
start-up race, and can be checked with `static_assert`.

`constexpr` allows a function or variable to be evaluated at compile time;
`consteval` requires it. `constinit` guarantees a variable is initialized at compile time
(no static initialization order problems) without making it `const`. C++20 allows
`std::vector` and `std::string` inside a constant evaluation as long as the memory is
freed before the evaluation ends, and many standard algorithms are `constexpr`.

### Worked example: the crystal position table

MiniDAQ's reference geometry (the numbers are typical values, not NeuroLF's real ones) is
a ring of 24 detector blocks, three blocks deep axially, each with 16 by 16 crystals:
18,432 crystals in total. Crystal ids pack the ring index and the position around the
ring, and the helpers decompose them with integer arithmetic that the compiler can check:

```{.cpp include="minidaq/include/minidaq/core/geometry.hpp" lines="1-56"}
```

The transaxial positions need sine and cosine. `std::sin` and `std::cos` are not
`constexpr` in C++20 or C++23 (GCC accepts them in constant expressions as an extension,
Clang rejects them; the C++26 working draft finally makes them `constexpr`). MiniDAQ
provides a small `constexpr` implementation with range reduction to $[-\pi/4, \pi/4]$ and a
Taylor series, and a unit test checks it against `std::sin`/`std::cos` to $10^{-13}$ over
thousands of points. The table itself is an immediately invoked lambda:

```{.cpp include="minidaq/include/minidaq/core/geometry.hpp" snippet="table"}
```

The finished array of 384 points lives in the read-only data section of the binary. At
run time there is no initialization code at all, which you can confirm with `nm -C` or by
looking for the values in `objdump -s -j .rodata`.

When is compile-time computation the wrong choice? When the data is large (a 3D system
matrix for reconstruction is gigabytes), when it depends on a calibration file measured on
the real scanner, or when it would slow the build noticeably. Crystal *positions* from the
mechanical design are a good fit; crystal *gains* from a calibration run (Chapter 26) are
not.

## Undefined behavior: a tour and the tools that find it

### The intuition

The C++ standard says that some operations have [undefined behavior]{.idx} (UB): the
standard imposes no requirements at all on what happens. That is not "the result is
unpredictable"; it is "the compiler may assume this never happens". Optimizers use that
assumption aggressively. A signed overflow check written after the overflow
(`if (total + x < total)`) can be deleted, because signed overflow "cannot happen". A null
check after a dereference can be deleted, because the dereference "proved" the pointer
was not null. Programs with UB often work perfectly at `-O0`, fail at `-O2`, and change
behavior with the next compiler release.

For a medical device, UB is a hazard in the ISO 14971 sense: a defect whose effect cannot
be bounded by analysis. The only reliable defense is to keep it out of the code, and to
run tools that catch it.

### The five classes you will meet in a DAQ

**1. Lifetime errors.** Use after free, use after scope, dangling views, double free.
Caught by AddressSanitizer (`heap-use-after-free`, `stack-use-after-return`,
`attempting double-free`).

**2. Bounds errors.** Off-by-one writes into histograms, reading past the end of a
packet. Caught by AddressSanitizer for heap, stack and global arrays; `std::span` and
`std::array::at()`, and libstdc++'s `_GLIBCXX_ASSERTIONS` mode, add cheap checks on
`operator[]` (Chapter 7 enables it in hardened builds).

**3. Aliasing and alignment.** Reading a `std::uint64_t` through a pointer cast from a
byte buffer. The address may be misaligned (UB, and a real crash on some ARM targets),
and the object you read was never created as a `uint64_t` (strict aliasing). Caught by
UBSan's `alignment` check; the fix is `std::memcpy` or `std::bit_cast`, which compile to a
single load.

**4. Arithmetic.** Signed integer overflow is UB; unsigned arithmetic is defined to wrap
modulo $2^N$. Shifting by a negative amount or by at least the width of the (promoted)
type is UB, and so is converting a floating-point value to an integer type that cannot
represent it. Caught by UBSan (`signed-integer-overflow`, `shift`,
`float-cast-overflow`).

Why the asymmetry between signed and unsigned? Historically, C supported machines with
different signed representations, so the result of signed overflow could not be specified
portably; leaving it undefined also lets compilers assume `i + 1 > i` for signed loop
counters, which enables loop optimizations. Unsigned types were defined from the start as
modular arithmetic. C++20 mandates two's complement representation, but signed overflow
remains UB. The practical lesson: use unsigned types for bit patterns and modular
counters (hardware timestamps that wrap), and signed types for quantities where
negative values are meaningful (time differences). The opening story is the mirror image:
unsigned arithmetic is *defined* to wrap, so the bug was not UB at all, just a wrong
model. Defined behavior is necessary, not sufficient.

**5. Data races.** Two threads access the same memory location, at least one writes, and
there is no synchronization: UB. Caught by ThreadSanitizer, which is the subject of
Chapter 3.

### The tools

| Tool | Catches | Typical slowdown | How MiniDAQ uses it |
|---|---|---|---|
| Compiler warnings (`-Wall -Wextra -Wpedantic -Wconversion -Wshadow ...`) | Many conversions, shadowing, some lifetime bugs | none | Every target, with `-Werror` |
| AddressSanitizer (ASan) | Lifetime and bounds errors, leaks | about 2x | `asan-ubsan` preset, every CI run |
| UndefinedBehaviorSanitizer (UBSan) | Overflow, shifts, alignment, null, bad casts | small | combined with ASan |
| ThreadSanitizer (TSan) | Data races, some deadlocks | 5x to 15x | `tsan` preset from Chapter 3 |
| MemorySanitizer (MSan) | Reads of uninitialized memory | about 3x | not used: needs every library rebuilt with it |
| Valgrind memcheck | Lifetime, uninitialized reads | 20x to 50x | occasional, for binaries you cannot rebuild |

Two practical points that trip up teams:

- **Make sanitizer findings fatal.** By default UBSan prints a message and continues. In
  CI that means a green build with a UB report buried in the log. MiniDAQ compiles with
  `-fno-sanitize-recover=all` and runs tests with `halt_on_error=1`.
- **Instrument everything in the process.** For TSan in particular, uninstrumented code
  (including a pre-built GoogleTest) produces false reports. MiniDAQ applies sanitizer
  flags globally through CMake rather than per target:

```{.cmake include="cmake/Sanitizers.cmake"}
```

### Warnings as a team contract

The warning flags live on an interface target that every MiniDAQ target links, so they
apply to MiniDAQ's code and never to third-party code pulled in by FetchContent:

```{.cmake include="cmake/Warnings.cmake"}
```

`-Wconversion` and `-Wsign-conversion` are noisy on old code and invaluable on new code:
they flag every implicit narrowing, which is exactly where unit and range bugs hide.
Starting a project with them on costs a few `static_cast`s; adding them to a 200,000-line
codebase later costs weeks. If your team's codebase does not use them, that is a good
question for your first weeks, not a reason to turn them on everywhere in your first week.

### Worked example: hunting five bugs with sanitizers

Exercise 1.4 gives you five small functions with one UB bug each. The point of the
exercise is the method, so here is what a session looks like for one of them. The test
`UbHunt.CrystalLabel` passes in a normal debug build. Under the `asan-ubsan` preset:

```text
$ ctest --preset asan-ubsan -R e4_ub_hunt/starter/UbHunt.CrystalLabel --output-on-failure
==6619==ERROR: AddressSanitizer: heap-use-after-free on address 0x506000000560
READ of size 2 at 0x506000000560 thread T0
    #0 ... in std::string::basic_string(const std::string&)
    #1 ... in ex::label_and_extend(...) ub_snippet.cpp:34
freed by thread T0 here:
    #3 ... in std::vector<std::string>::_M_realloc_append ...
    #4 ... in ex::label_and_extend(...) ub_snippet.cpp:32
```

The report names the bug class (use after free), the line that read freed memory (the
`return first;`) and the line that freed it (the `emplace_back` that reallocated). You do
not need to understand the function before reading the report; the report tells you
where to look. All five starter bugs are caught this way: two by ASan (the histogram
overflow and this one) and three by UBSan (signed overflow, misaligned load, shift
exponent).

::: box-mistakes
- Treating "the tests pass" as evidence of no UB.
- Running sanitizers only before releases. Run them on every merge request.
- Suppressing a sanitizer report instead of understanding it.
- Checking for overflow after the overflow.
:::

::: box-regulated
IEC 62304 asks for documented unit acceptance criteria and evidence that units meet them
(Chapter 14). For class C software it lists additional acceptance criteria to consider,
among them initialization of variables, memory management and memory overflows, and
boundary conditions: exactly the defect classes this chapter's tools find. Your evidence for this chapter's
practices is concrete and auditable:

- The **coding standard** (warning set, `-Werror`, banned constructs) is a document in the
  repository, referenced from the software development plan, and enforced by the build.
- **Sanitizer runs in CI** produce logs attached to each release's test evidence. "All
  unit tests pass under ASan and UBSan with zero reports" is a verifiable acceptance
  criterion.
- **Strong types and `[[nodiscard]]`** are risk control measures by design (ISO 14971
  calls them inherent safety by design): they make a class of hazardous mistakes (mixing
  units, ignoring a write error) impossible to compile. Record them as such in the risk
  file, with the test that proves the protection (a compile-fail or trait test).
- **Toolchain versions** are part of the configuration you release; a different compiler
  can turn latent UB into a visible failure. Chapter 20 records them in every release.
:::

::: box-askteam
1. Which C++ standard and which compilers (and versions) does the NeuroLF DAQ build with,
   and is there a plan to move forward?
2. Is there a written coding standard (CERT, MISRA C++:2023, AUTOSAR, in-house)? Who
   approves deviations?
3. Are exceptions allowed in the acquisition code? Is any part built with
   `-fno-exceptions`?
4. Do the CI pipelines run AddressSanitizer, UBSan and ThreadSanitizer, and on which
   test suites?
5. How are physical units and timestamps represented today (raw integers, a units
   library, conventions in names)?
:::

## Exercises {.unnumbered}

Solutions and model answers are in the solutions manual. Every coding exercise has a
starter and a solution under `exercises/ch01/` with shared acceptance tests. Build your
starters with:

```bash
cmake --preset debug -DMINIDAQ_BUILD_STARTERS=ON
cmake --build --preset debug
ctest --preset debug -L starter -R ch01
```

**Exercise 1.1 (E): Strong types for picoseconds and keV.** *Goal:* write `Picoseconds`
and `KeV` types that refuse to mix at compile time and cost nothing at run time.
*Starter:* `exercises/ch01/e1_strong_types/starter/units.hpp`. *Acceptance:* the tests
in `tests/test_units.cpp` pass; they check with `std::is_invocable_v` that
`Picoseconds + KeV` and `Picoseconds + int64_t` are rejected, that the types are
trivially copyable and the size of their representation, and that same-unit arithmetic
works. *Time:* 30 to 45 minutes.

**Exercise 1.2 (M): From raw pointers to the Rule of 0.** *Goal:* refactor a legacy
`EventBuffer` that owns a raw `new[]` array into a class that declares no special
members, exposes `std::span`, has deep copies and `noexcept` moves. *Starter:*
`exercises/ch01/e2_rule_of_zero/starter/event_buffer.hpp`. *Acceptance:* the five tests
pass under the `asan-ubsan` preset (the starter dies with a double free). *Time:* 45 to
60 minutes.

**Exercise 1.3 (M): A parser that cannot be crashed.** *Goal:* implement
`parse_single(std::span<const std::byte>) -> Expected<Single, ParseError>` for the raw16
format and fuzz it with ten malformed inputs plus a 200,000-iteration mutation loop.
*Starter:* `exercises/ch01/e3_parse_single/starter/`. *Acceptance:* round trip, the ten
named malformed inputs map to the right errors, and the mutation loop finds no crash under
ASan and no accepted record that violates the invariants. *Time:* 60 to 90 minutes.

**Exercise 1.4 (H): Five seeded UB bugs.** *Goal:* find and fix five undefined-behavior
bugs using only sanitizer output, and document each in `FINDINGS.md` (class, tool, fix).
*Starter:* `exercises/ch01/e4_ub_hunt/starter/`. *Acceptance:* the five tests pass under
`asan-ubsan` with no sanitizer report. *Time:* 90 minutes.

**Exercise 1.5 (M, extra): A crystal geometry table built by the compiler.** *Goal:* a
`consteval` function that returns the positions of N crystals on a ring, using
`minidaq::cmath::sincos`. *Starter:* `exercises/ch01/e5_constexpr_lut/starter/`.
*Acceptance:* points lie on the circle to $10^{-9}$ mm, spacing matches the pitch, and
the table is a constant expression. *Time:* 45 minutes.

**Exercise 1.6 (M, extra): Constraining event processors with concepts.** *Goal:* define
`SingleSink` and `SingleFilter` concepts and a constrained `feed()`. *Starter:*
`exercises/ch01/e6_event_concepts/starter/`. *Acceptance:* the trait checks accept the
good types and reject the bad ones, and `feed` keeps exactly the singles inside a
350 to 650 keV window. *Time:* 45 to 60 minutes.

## MiniDAQ milestone: repository skeleton and core types {.unnumbered}

::: box-milestone
**Goal.** A repository that builds with one command on GCC and Clang, contains the core
types every later chapter uses (`Picoseconds`, `KeV`, `CrystalId`, `Single`,
`Coincidence`, the scanner geometry, the raw16 parser), and runs its unit tests under
ASan and UBSan in CI.

**Starting point:** tag `ch00` (an empty repository with only a README). **End point:**
tag `ch01`.
:::

**Step 1: the top-level CMake project.** Read the version from a `VERSION` file so the
book, the code and the release notes always agree, and expose options for tests,
exercises and sanitizers:

```{.cmake include="CMakeLists.txt"}
```

**Step 2: presets.** `CMakePresets.json` defines `debug` (GCC), `release`,
`clang-release`, `asan-ubsan`, `tsan` and `coverage`, each with its own build directory
under `build/`. Dependencies are cached once in `.deps/`. Presets make the build
reproducible across developers and CI: "configure with the `asan-ubsan` preset" means the
same flags everywhere.

**Step 3: dependencies.** GoogleTest is fetched at an exact commit, not a branch or a
floating tag, so every build of a given MiniDAQ version uses identical test framework
sources (Chapter 14 explains why this is SOUP configuration management):

```{.cmake include="cmake/Dependencies.cmake"}
```

**Step 4: the core library and its tests.** Add the headers shown in this chapter under
`minidaq/include/minidaq/core/` and `minidaq/include/minidaq/format/`, the parser
implementation, and unit tests for each. The tests carry requirement tags in comments
(`// REQ: SRS-CORE-001`); Chapter 14 turns them into a traceability matrix.

**Step 5: CI.** `.github/workflows/ci.yml` builds and tests three presets on every push:
`debug`, `clang-release` and `asan-ubsan`. The same gates run locally with
`ci/run_all.sh`.

**Definition of done.**

- `ci/run_all.sh` passes: all unit tests and exercise solutions green on GCC debug, Clang
  release and Clang ASan+UBSan, with zero warnings under `-Werror`.
- `static_assert(sizeof(Single) == 16)` holds.
- The raw16 parser rejects every malformed input in the test suite.

**Verification output** (the author's run, Ubuntu 24.04, GCC 13.3, Clang 18.1.3):

```text
$ ci/run_all.sh
=== preset: debug ===          100% tests passed, 0 tests failed out of 39
=== preset: clang-release ===  100% tests passed, 0 tests failed out of 39
=== preset: asan-ubsan ===     100% tests passed, 0 tests failed out of 39
=== all gates passed: debug clang-release asan-ubsan ===
```

Commit and tag: `git tag ch01`.

## Check yourself {.unnumbered}

Answer without notes; model answers are in the solutions manual.

1. When does `std::string_view` dangle? Give three different situations.
2. Why is signed overflow undefined behavior while unsigned wraparound is not, and which
   would you use for a 32-bit hardware timestamp counter?
3. What does `[[nodiscard]]` buy you on an error type, compared with on a single function?
4. A class has a user-written destructor and no other special members. What happens when
   you copy it, and what happens when you `std::move` it?
5. Why does `std::vector<T>` sometimes copy elements during reallocation instead of moving
   them, and how do you prevent it?
6. You must pass "the singles in this batch" to a function that only reads them. What
   parameter type do you choose, and what does the caller have to guarantee?
7. Why does MiniDAQ store time as `int64_t` picoseconds rather than `double` seconds?
   Quantify the precision problem.
8. Name the sanitizer that catches each of: a misaligned load, a heap use after free, a
   data race, a shift by 40 of an `int`. Which one cannot be combined with the others in a
   single build?
9. Why are exceptions acceptable when parsing a configuration file but not when parsing a
   network packet in MiniDAQ?
10. What is the difference between `constexpr`, `consteval` and `constinit`?

## Summary {.unnumbered}

- Every object has one owner. Owning types live in members and locals; views (`span`,
  `string_view`, references) travel through parameters.
- Prefer the Rule of 0. Write the Rule of 5 only in small wrappers around raw resources,
  and make moves `noexcept`.
- Views dangle when their storage dies or reallocates; ASan finds what the compiler
  cannot.
- Strong types for time, energy and ids make unit errors compile errors at zero run-time
  cost. Time is `int64_t` picoseconds.
- `[[nodiscard]]` on error types plus `-Werror` makes ignoring an error a build failure.
- The per-event path never throws; it returns `Expected` values and counts errors.
  Exceptions are for start-up and control-plane failures.
- Concepts state what a template needs; use them in hot code, virtual interfaces at
  hardware boundaries.
- `constexpr`/`consteval` tables cost nothing at run time and are checked by the compiler.
- Undefined behavior lets the optimizer assume your bug cannot happen. Build every target
  with strict warnings and run every test under ASan+UBSan (and TSan from Chapter 3).
- Strict tooling is regulatory evidence: the coding standard, the sanitizer logs and the
  toolchain versions belong in the design history.

## Further reading {.unnumbered}

- Bjarne Stroustrup, *A Tour of C++*, 3rd edition, Addison-Wesley, 2022. The fastest
  complete overview of C++20.
- Bjarne Stroustrup and Herb Sutter (eds.), *C++ Core Guidelines*,
  <https://isocpp.github.io/CppCoreGuidelines/>. Sections C (classes, including C.20 and
  C.21 on default operations), R (resource management) and ES (expressions).
- Klaus Iglberger, *C++ Software Design*, O'Reilly, 2022. Value semantics, type erasure
  and design patterns in modern C++.
- John Regehr, "A Guide to Undefined Behavior in C and C++", parts 1 to 3, blog post,
  2010, <https://blog.regehr.org/archives/213>.
- Clang documentation: AddressSanitizer, UndefinedBehaviorSanitizer and
  ThreadSanitizer, <https://clang.llvm.org/docs/>.
- cppreference, `std::expected`, <https://en.cppreference.com/w/cpp/utility/expected>.
- Herb Sutter, "Zero-overhead deterministic exceptions: Throwing values", WG21 paper
  P0709. A clear explanation of why many domains avoid today's exceptions.
- Joshua Berne, Timur Doumler, Andrzej Krzemieński et al., "Contracts for C++", WG21 paper
  P2900, the contracts design adopted for C++26.
