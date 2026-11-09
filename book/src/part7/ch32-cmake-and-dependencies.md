# CMake and dependency management: the build as an interface {#ch32}

::: box-why
A build that works is not the same as a build that others can use. MiniDAQ's CMake project has built
the server, the tests, a C++ projector with a Python module and almost 150 exercises since Chapter
1, but only in one way: from this repository, on a machine set up as the CI runners are. The day
another group wants the projector in its own C++ tool, the day a new colleague needs to run what CI
runs for one configuration, the day the Python module has to be installed on a machine without a
MiniDAQ build, the build becomes an interface, and an interface needs the same care as code: a
contract, tests, and versions. This chapter treats it that way, measures where the build's time
goes, and adds the tooling that keeps every new line of code in one style.
:::

**A day in the life.** A physicist in the reconstruction group wants to try a 3D variant of the
projector in their own C++ program. They clone MiniDAQ, build it, and point their program at the
build tree: `-I/home/them/minidaq/recon/include` and `-L/home/them/minidaq/build/release/recon`. It
works. A month later a colleague runs the program on another machine and it does not build, because
the paths are of a directory that exists only on the first machine. They copy the projector's
sources into their own repository instead. That works too, until a bug is fixed in MiniDAQ's
projector, and the copy keeps the bug for a year, because nobody remembers the copy exists. Neither
of them did anything unusual. MiniDAQ had simply never said how its library is meant to be used from
outside.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Describe a library by its usage requirements (`PUBLIC`, `PRIVATE`, `INTERFACE`) instead of by
   directory settings, and say what each one passes on to the targets that link it.
2. Use generator expressions for what differs between building and installing, between
   configurations, and between compilers.
3. Write presets with a workflow per configuration, choose compilers with a toolchain file, and say
   what a cross toolchain file adds.
4. Install a library as a CMake package (an export set, a configuration file, a version file) that
   another project finds with `find_package` from any prefix, and test that it does.
5. Pin dependencies so that every build of a version uses the same bytes, decide what to fetch and
   what to find, and keep the pins and the SOUP list in agreement.
6. Build a Python wheel of a C++ module from the same CMake project with scikit-build-core.
7. Measure where a build's time goes, and cut what a change to one header costs.
8. Introduce a formatting rule into an existing codebase without reformatting it, and check it on
   the lines each change touches.

## Prerequisites and estimated time {.unnumbered}

Chapter 1 (the CMake project and its presets), Chapter 7 (the warnings and static analysis), Chapter
14 (the SOUP list), Chapter 20 (the tool list, reproducible builds and the gate self-test) and
Chapter 29 (the projector and its Python module). Reading: about 3 hours. Exercises: 2 hours.
Milestone: 5 hours. If time is short, do Exercise 32.1.

## Targets and what they pass on

Chapter 1 wrote CMake as a recipe that worked. This chapter reads it as a description of a graph:
every library and executable is a target, and every target has properties that say how to compile it
and how to use it. The second half is what matters for an interface. A property set with `PRIVATE`
applies to the target's own sources; with `INTERFACE` it applies only to the targets that link it;
with `PUBLIC` it applies to both. These are the target's *usage requirements*, and CMake propagates
them along every `target_link_libraries` edge, transitively, as far as they are public.

MiniDAQ's control library shows each kind in one call:

```cmake
target_link_libraries(minidaq_control PUBLIC minidaq::core nlohmann_json::nlohmann_json
                      PRIVATE OpenSSL::SSL OpenSSL::Crypto minidaq::warnings)
```

The core and the JSON library are public, because `minidaq_control`'s headers include theirs: a
program that includes `acquisition_config.hpp` must be able to find `nlohmann/json.hpp`, and must
link the core whose types appear in the control library's functions. OpenSSL is private, because
only `.cpp` files use it: a program that links the control library gets OpenSSL linked (a static
library's private dependencies must still be linked into the final program), but does not get
OpenSSL's include directories, and cannot include its headers by accident. The warnings are private,
because they are how MiniDAQ compiles its own code, not something a user of the library should
inherit.

The warnings target is itself worth a look, because it is the pattern for every build setting that
should not leak:

```cmake
add_library(minidaq_warnings INTERFACE)
target_compile_options(minidaq_warnings INTERFACE -Wall -Wextra ... -Werror)
```

An `INTERFACE` library has no sources; it exists to carry usage requirements. Linking it privately
applies its options to one target's sources and to nothing else. Chapter 7 chose this over the older
directory commands (`add_compile_options`, `include_directories`, `add_definitions`), which apply to
every target in the directory and below, including the third-party code that FetchContent adds.
GoogleTest does not compile without warnings under MiniDAQ's `-Wconversion`, and it does not have
to: the warnings never reach it.

Figure [](#fig-ch32-targets) draws the call as a graph.

```{.figure #fig-ch32-targets src="book/figures/tikz/ch32/targets.tex" caption="What minidaq_control passes on. Its public dependencies reach every program that links it; its private ones stay with its own sources, except that a static library's private libraries must still be linked." alt="minidaq_control in the middle with solid arrows labelled PUBLIC to minidaq::core and nlohmann_json, and dashed arrows labelled PRIVATE to OpenSSL::SSL and minidaq::warnings. Below, a program that links it gets core's and json's include directories and links, OpenSSL linked but not its headers, and none of the warnings." width="90%"}
```

The rule that follows is short. State each requirement on the target that has it, with the narrowest
scope that is true: private unless a header needs it. A requirement that is public when it should be
private is not an error the compiler reports. It is a dependency that every user silently takes on,
and that breaks them when it changes. Exercise 32.1's starter makes the library's build definition
`PULSE_CHECKED` public, and its consumer refuses to compile with it: a definition that changed a
type's layout in a header would give the library and its users two types under one name, which no
tool reports.

### Generator expressions

Some values are not known when `CMakeLists.txt` is read. The path of a target's output depends on
the generator and the configuration; a debug flag applies only to the Debug configuration of a
multi-configuration generator; an include directory differs between the build tree and an installed
copy. Generator expressions, the `$<...>` syntax, are evaluated when CMake writes the build files,
once per configuration, and they are how a target states such values.

Three kinds cover most uses. `$<TARGET_FILE:minidaq_server>` is the path of a target's file, which
MiniDAQ's tests use to run its programs without knowing the build directory's layout.
`$<$<CONFIG:Debug>:-Og>` is a value that applies only under a condition: `$<cond:value>` is `value`
when `cond` is 1 and empty otherwise. And `$<BUILD_INTERFACE:...>` and `$<INSTALL_INTERFACE:...>`
give a value for the target as it is built and for the target as it is installed, which the next
sections need.

Generator expressions are also how a build goes wrong quietly. They are not evaluated in `if()`, so
`if($<CONFIG:Debug>)` tests a non-empty string and is always true. `message()` prints them
unevaluated. And a misspelled one is often not an error but an empty string. Use `file(GENERATE
OUTPUT ... CONTENT "$<...>")` to see what an expression evaluates to, per configuration.

## Presets, workflows and toolchains

Chapter 1 introduced `CMakePresets.json`: a configuration's generator, build directory and cache
variables, named, so that `cmake --preset release` configures the same build on every machine.
Building and testing were two more commands with their own presets. MiniDAQ has ten configurations
(debug, release, profile, clang-release, gcc-cxx23, hardened, asan-ubsan, tsan, fuzz and coverage),
and CI runs six of them on every push. A developer who wanted to know whether a change would pass
the `tsan` job had to know the three commands and their order.

A workflow preset (presets file version 6, CMake 3.25) names the steps as one:

```json
{
  "name": "tsan",
  "steps": [
    {"type": "configure", "name": "tsan"},
    {"type": "build", "name": "tsan"},
    {"type": "test", "name": "tsan"}
  ]
}
```

`cmake --workflow --preset tsan` configures, builds and runs the tests of that configuration and
stops at the first step that fails. It is the whole gate of one configuration, the same on a laptop
as in CI, and every configuration has one. Two things keep that true. A test preset can name another
configuration's build directory by mistake, and a configuration added later can lack its workflow;
`tools/check_presets.py` (test `docs.presets`, SRS-BLD-002) checks that every configuration that is
not hidden has a build, a test and a workflow preset of its name, that each workflow runs exactly
those three in order, and that every preset the CI matrix names exists. The test that shows it can
fail removes the `tsan` workflow and expects the error that names it.

Presets inherit, which is how MiniDAQ avoids repeating itself. A hidden preset `base` sets the
generator (Ninja), the build directory and the shared FetchContent directory; hidden presets `gcc`
and `clang` choose the compiler; `release` inherits `base` and `gcc` and adds its build type. Until
this chapter, `gcc` and `clang` set the cache variable `CMAKE_CXX_COMPILER`. They now name a
toolchain file each:

```cmake
# cmake/toolchains/clang.cmake
set(CMAKE_C_COMPILER clang)
set(CMAKE_CXX_COMPILER clang++)
```

For a native build the two are equivalent. The reason to change is the next step. A toolchain file
is read before the first `project()` call, where CMake inspects the compiler, and it is the one
place for everything that describes the target platform rather than the project. A cross toolchain
file for an ARM acquisition computer would add `CMAKE_SYSTEM_NAME` and `CMAKE_SYSTEM_PROCESSOR`, a
`CMAKE_SYSROOT` with the target's headers and libraries, and `CMAKE_FIND_ROOT_PATH_MODE_*` settings
so that `find_package` looks in the sysroot and never in the build machine's `/usr`. With the
compilers already in toolchain files, that build is a new file and a new preset that inherits it,
not a change to every preset.

One file of presets is shared and reviewed; a developer's own settings (a local compiler, a ccache
launcher, a different build directory) belong in `CMakeUserPresets.json`, which may inherit from the
project's presets and is not committed. Exercise 32.2 writes the presets of a small project whose
`asan` configuration must find a read past an array that no test sees in a normal build. Its starter
compiles with `-fsanitize=address` but does not link with it, and the build fails: a sanitizer is a
runtime library as well as an instrumentation, and both halves must be in the preset.

Figure [](#fig-ch32-presets) shows the whole set.

```{.figure #fig-ch32-presets src="book/figures/tikz/ch32/presets.tex" caption="MiniDAQ's configure presets, from CMakePresets.json. Three hidden presets carry the shared settings and the two compilers; the ten visible ones each inherit base and one compiler and have a workflow of their own." alt="A tree. The hidden preset base, with Ninja, the shared deps directory and C++20, above the hidden presets gcc and clang. Under gcc: debug, release, profile, gcc-cxx23 and hardened. Under clang: clang-release, asan-ubsan, tsan, fuzz and coverage. A note says each visible preset has a workflow that configures, builds and tests." width="85%"}
```

## Installing a library as a package

The physicist in the opening story needed three things from MiniDAQ: the headers, the library, and a
statement of how to use them (which include directory, which other libraries, which C++ standard).
The first two are files. The third is what a CMake package provides: a file that another project's
`find_package(recon)` reads, and that creates an *imported target* `recon::projector` carrying the
same usage requirements the target has in MiniDAQ's own build. The user writes three lines:

```{.cmake include="recon/tests/consumer/CMakeLists.txt" snippet="consumer"}
```

and gets the include directory, the C++20 requirement and the thread library, from wherever the
package was installed. Making that work took four pieces, in `recon/CMakeLists.txt`.

**Usage requirements that are true in both places.** The target's include directory had been the
source tree's `recon/include`, an absolute path. Once installed, that directory may not exist. The
target now states one path for each context:

```{.cmake include="recon/CMakeLists.txt" snippet="usage"}
```

`BUILD_INTERFACE` is used inside this build; `INSTALL_INTERFACE` is written into the installed
package, relative to wherever the package lands. CMake refuses the old form outright when the target
is exported, which is the right behavior:

```text
CMake Error in recon/CMakeLists.txt:
  Target "recon_projector" INTERFACE_INCLUDE_DIRECTORIES property contains
  path:

    "<source tree>/recon/include"

  which is prefixed in the source directory.
```

The snippet's other change is the subtler one. The warnings target is linked privately, and a
private dependency of a static library is still exported, as a link dependency: the user's program
must link whatever the library's objects need. `minidaq::warnings` is not installed, so the export
would name a target the user cannot have:

```text
CMake Error: install(EXPORT "reconTargets" ...) includes target "recon_projector" which requires
target "minidaq_warnings" that is not in any export set.
```

`$<BUILD_INTERFACE:minidaq::warnings>` keeps it in this build and out of the package. It is a
compile setting, not a link dependency, and the export is now honest about it.

**An export set, a configuration file and a version file.** These are installed together:

```{.cmake include="recon/CMakeLists.txt" snippet="install"}
```

`install(TARGETS ... EXPORT reconTargets)` installs the archive and records the target in an export
set; `install(EXPORT ...)` writes that set as `reconTargets.cmake`, a file that creates
`recon::projector` as an imported target with paths relative to its own location. The configuration
file is what `find_package` looks for, and it is short:

```{.cmake include="recon/cmake/reconConfig.cmake.in"}
```

`find_dependency(Threads)` is there because the target's interface names `Threads::Threads`: when
the user's project reads `reconTargets.cmake`, that target must already exist, so the package finds
its own public dependencies first. `@PACKAGE_INIT@` and `check_required_components` come from
`configure_package_config_file`, which makes the file relocatable and reports a requested component
that the package does not have. The version file decides which requests the package satisfies.
MiniDAQ is before 1.0, where a minor version may change an interface, so it uses `SameMinorVersion`:
0.7.0 satisfies `find_package(recon 0.7)` and refuses 0.6 and 0.8. After 1.0, `SameMajorVersion`
would say what semantic versioning promises; `AnyNewerVersion` promises more than most libraries
keep.

**Components.** Every `install()` names the component `recon_dev`, so `cmake --install build
--component recon_dev` installs this package alone, and the wheel of the next section installs a
different component of the same build.

**A test that the package works.** None of this is visible in MiniDAQ's own build, where the target
is used directly; a mistake in the package shows only in someone else's project. So the test
`cmake.consumer` (SRS-BLD-001) is someone else's project:

```{.cmake include="recon/tests/consumer_test.cmake" snippet="test"}
```

It installs the component into an empty prefix, reads every installed `.cmake` file for the paths of
this build and this source tree, configures `recon/tests/consumer` with only that prefix on its
search path, builds it, and runs it; the program checks the projector's defining property, that
`<Ax, y>` equals `<x, A^T y>` for random `x` and `y`. It runs on every build that is not
instrumented (a sanitizer's flags would have to be the consumer's too). Exercise 32.1 goes one step
further for its library: it copies the installation to another directory before using it, which is
what a relocatable package must survive.

Figure [](#fig-ch32-package) puts the installed files next to what each one does.

```{.figure #fig-ch32-package src="book/figures/tikz/ch32/package.tex" caption="An installed CMake package and what find_package does with it: the version file decides, the configuration file finds the package's public dependencies, and the export set creates the imported target." alt="Left, the installed tree: include/recon/projector.hpp, lib/librecon_projector.a, and lib/cmake/recon with reconConfig.cmake, reconConfigVersion.cmake and reconTargets.cmake. Right, a chain: find_package(recon 0.7), version SameMinorVersion, find_dependency(Threads), imported recon::projector, each linked by a dotted line to the file that provides it. A note says the cmake.consumer test builds someone else's project against the installation." width="85%"}
```

## Dependencies: pinned, found, reviewed

MiniDAQ has had the same dependency policy since Chapter 1, and this chapter keeps it after looking
at the alternatives. Each third-party library that becomes part of a build is fetched by
FetchContent at an exact pin, either a git commit or an archive with its SHA-256:

```cmake
FetchContent_Declare(nlohmann_json
  URL      https://github.com/nlohmann/json/releases/download/v3.12.0/json.tar.xz
  URL_HASH SHA256=42f6e95cad6ec532fd372391373363b62a14af6d771056dbfc86160e6dfff7aa
  SYSTEM)
```

A tag is not a pin: a tag can be moved, and a branch moves by design. A commit hash or an archive
hash names bytes, which is what the SOUP list must identify and what a reproducible build needs.
`SYSTEM` marks the dependency's headers as system headers, so MiniDAQ's warnings do not fire inside
them when MiniDAQ includes them. The presets set `FETCHCONTENT_BASE_DIR` to one `.deps` directory
for every configuration and `FETCHCONTENT_UPDATES_DISCONNECTED`, so ten build directories share one
download and a configure does not go to the network once the sources are there.

Not everything is fetched. OpenSSL is a platform library: the operating system image provides it and
its security updates (Chapter 17), so it is found with `find_package(OpenSSL 3.0 REQUIRED)`, and the
SBOM records the version the build found. The rule is about who owns the updates. A library whose
security fixes must arrive with the operating system is found; a library whose exact version is part
of the product's verified state is pinned. `MINIDAQ_USE_SYSTEM_DEPS=ON` switches the pinned ones to
`find_package` as well, for a distribution's offline build, at the cost of the pins.

Two checks keep the policy true. `tools/check_soup.py` (test `docs.soup`) reads the pins from
`cmake/Dependencies.cmake` and fails if the SOUP list does not name each one's version and pin, or
if a shipped item lacks a review for the current minor version; the gate self-test changes
GoogleTest's pin and expects the failure. And `tools/make_sbom.py` writes the CycloneDX SBOM from
the same pins, which CI scans for known vulnerabilities (Chapter 17).

A package manager, Conan or vcpkg, would manage the same pins with a lock file and binary caches,
and for a project with dozens of dependencies and several platforms it is the better tool. MiniDAQ
has four pinned C++ dependencies, all built from source with the project's flags, and every one of
them is reviewed as SOUP; a second system that resolves versions would add a tool to validate and a
place where a version can change without the SOUP list. Conan was proposed when Chapter 31 chose its
tools and was not approved. The decision is recorded in ADR 0027, with the condition that would
change it: dependencies that need prebuilt binaries for several platforms.

Figure [](#fig-ch32-deps) sorts them by who owns their updates.

```{.figure #fig-ch32-deps src="book/figures/tikz/ch32/deps.tex" caption="MiniDAQ's dependencies, from cmake/Dependencies.cmake. Four are fetched at an exact pin and built with the project's flags; two are found on the platform, whose image owns their updates." alt="Two rows. Fetched at a commit or hash: nlohmann_json 3.12.0 in the product, pybind11 3.1.0 for the projector module, GoogleTest 1.15.2 for tests only, Google Benchmark 1.9.1 for benchmarks only. Found on the platform: OpenSSL 3.0 for TLS and signatures, Python 3 for the module's headers. A note says each is on the SOUP list and in the SBOM." width="95%"}
```

::: box-mistakes
- **A dependency pinned by tag or branch.** It names a moving reference, not bytes. Pin a commit or
  an archive hash.
- **`include_directories()` and `add_compile_options()` at the top level.** They apply to every
  target below, third-party code included. State requirements on targets.
- **Everything `PUBLIC`.** Every user then depends on everything. Private unless a header needs it.
- **An absolute path of the source tree in an exported target.** It names one machine. Use
  `BUILD_INTERFACE` and `INSTALL_INTERFACE`.
- **A package that is never used from outside in a test.** Its mistakes show only in someone else's
  project. Install it into an empty prefix and build a consumer against it.
- **A sanitizer in the compile flags only.** Its runtime is a library: link with it too.
- **A generator expression in `if()`.** It is a string there, and a non-empty string is true.
:::

## A wheel from the same project

Chapter 29 built the projector's Python module, `recon_cpp`, as a target of the main build, which
CTest imports from the build directory. That serves MiniDAQ's tests. It does not serve a physicist
who wants `import recon_cpp` in their own environment, on a machine without a MiniDAQ build. For
that, Python's packaging has the wheel: a zip file of the module and its metadata, which `pip`
installs.

The usual way to build a C++ extension's wheel is setuptools with a `build_ext` step that compiles
the sources itself, with its own list of files, flags and include directories. That is a second
build system describing the same module, and the two drift: a flag added in CMake is missing from
the wheel, and nothing notices until a number differs. scikit-build-core is a Python build backend
that runs CMake instead, and `recon/python/pyproject.toml` uses it to run MiniDAQ's own project:

```{.toml include="recon/python/pyproject.toml" snippet="skbuild"}
```

`cmake.source-dir` points at the repository's top, so the wheel is built by the same
`CMakeLists.txt` files as everything else. The defines switch off the tests, the benchmarks and the
exercises, so the build fetches only pybind11 and compiles only the projector. `build.targets`
builds the one target, and `install.components` installs the one component, which
`recon/CMakeLists.txt` defines only when scikit-build-core is running:

```cmake
if(SKBUILD)
  install(TARGETS recon_cpp LIBRARY DESTINATION . COMPONENT recon_python)
endif()
```

`SKBUILD` is set by scikit-build-core, so the install rule exists in a wheel build and nowhere else,
and the module lands at the root of the wheel. The result is 119 kB, holding one file of 263 kB
uncompressed, `recon_cpp.cpython-313-x86_64-linux-gnu.so`, and its metadata.

The test `recon.wheel` (SRS-BLD-003) builds the wheel with the build directory's Python, installs it
with `pip --target` into an empty directory, and runs the projector's existing tests,
`tools/test_recon_cpp.py`, against the installed module, with nothing of the build tree on the path.
Its first version passed for the wrong reason: Python puts the current directory on the module path,
CTest runs a test in the build directory, and the build directory holds the build's own `recon_cpp`,
which the tests imported. The test now runs from its empty work directory and also checks that the
imported module's file is the installed one. The CI job `python` runs it with scikit-build-core from
the lock file of Chapter 31, where version 1.1.2 is pinned (tool TL-38).

The wheel's tag is `linux_x86_64`: it is built for this machine's platform and Python, and pip
installs it only on a matching one. A wheel for distribution to other Linux machines is built in a
`manylinux` container against an old C library and repaired with `auditwheel`, which copies the
shared libraries it needs into it; `cibuildwheel` automates that for several Python versions. The
projector has no shared libraries beyond the C and C++ runtimes, so that step is small, but it is a
step MiniDAQ does not take, because its users build from source (assumption: confirm with team how
the physics group installs tools on its analysis machines).

## Where the build time goes

A build's speed is part of how a team works: a rebuild that takes a minute after every header change
is a minute the developer spends not testing. Before changing anything, measure.
`measurements/ch32/build_times.py` configures a fresh build directory with the release preset, then
times a clean build, a build with nothing to do, and the rebuild after touching each of four files.
On the book's machine (4 CPUs, GCC 13.3, Ninja, 4 jobs):

| Step | Time | Commands |
|---|---|---|
| Configure, sources present | 6.4 s | |
| Clean build of every target | 156.6 s | 453 |
| Build with nothing to do | 2.1 s | 2 |
| After touching `core/expected.hpp` | 84.5 s | 253 |
| After touching `core/crc32.hpp` | 12.7 s | 141 |
| After touching `src/core/crc32.cpp` | 2.9 s | 129 |
| After touching `apps/minidaq_send.cpp` | 1.6 s | 2 |

Two lines explain most of it. `expected.hpp` is included directly by 39 files and, through other
headers, by most of the code, so touching it rebuilds more than half of everything: 84.5 s of a
156.6 s clean build. And touching one source of the core library, `crc32.cpp`, compiles one file but
runs 129 commands, because the core is a static library and every program and test executable that
links it is linked again, 128 links in under 3 s. A leaf source, `minidaq_send.cpp`, compiles itself
and links one program.

Ninja knows what to rebuild because the compiler tells it. CMake compiles each file with `-MD -MF`,
the compiler writes every header it opened into a dependency file, and Ninja moves those lists into
its log after each compile. A header is a dependency of a file because the compiler opened it, not
because a `CMakeLists.txt` names it. That makes the dependency graph exact, and it makes the cost of
an include visible: every `#include` in a header is paid by every file that includes the header, at
every change to anything it includes.

The cure is physical design, an old subject (Lakos's book in Further reading is the classic). A
header includes what its declarations need and no more. A type used only by reference or pointer in
a header can be declared there (`struct Config;`) and defined where it is used. A large header that
changes often is split from the small, stable declarations most files need. Exercise 32.3 makes the
change on a small program whose `geometry.hpp` includes `config.hpp` to hold a copy of the
configuration: after the change, touching `config.hpp` compiles three files instead of eleven, and
its test asks Ninja for a dry run (`ninja -n`) to count them.

Some tools trade a different cost for speed: a compiler cache (ccache) reuses objects across clean
builds and branches, precompiled headers and unity builds compile shared headers once, and a linker
such as mold shortens the links. Each changes how the product is built, which for a shipped build is
a change with a tool review and a reproducibility check (Chapter 20). MiniDAQ uses none of them yet;
the measurements are the baseline against which one would be judged.

Figure [](#fig-ch32-buildtime) draws the measurement.

```{.figure #fig-ch32-buildtime src="book/figures/plots/ch32/buildtime.py" caption="Where the build time goes. Touching expected.hpp rebuilds more than half of the clean build; touching one source of the core library compiles one file and relinks 128 executables." alt="Horizontal bars in seconds: clean build 156.6 s with 453 commands, nothing to do 2.1 s with 2, touch core/expected.hpp 84.5 s with 253, touch core/crc32.hpp 12.7 s with 141, touch core/crc32.cpp 2.9 s with 129, touch minidaq_send.cpp 1.6 s with 2." width="85%" inputs="measurements/ch32/build-times.txt"}
```

## Formatting, checked on the lines you touch

MiniDAQ's coding standard (Chapter 7) has rules for errors, untrusted input, resources and
concurrency, each enforced by a tool or a test. It had no rule for formatting, and after 31 chapters
the code shows it: consistent within a file, mostly, and not across files. That costs more than
looks. A reviewer reads a diff where a reformatted line hides the one real change, and two
developers whose editors format differently produce diffs of each other's whitespace.

The usual remedy is to choose a style, run `clang-format` on every file once, and check every file
from then on. MiniDAQ measured that before doing it. With Google's style at 100 columns (the width
the code was written to), pointers to the left, and include blocks preserved:

```yaml
BasedOnStyle: Google
ColumnLimit: 100
DerivePointerAlignment: false
PointerAlignment: Left
IncludeBlocks: Preserve
```

`clang-format` would rewrite 1,883 lines in 308 of 619 C++ files, about 3.4% of the 54,616 lines
(`measurements/ch32/format-cost.txt`, measured after release 0.7.0). Small, but spread over half
the files, and every one of those lines would show the format commit in `git blame` instead of the
change that wrote it. The history of a line is how a regulated team
answers "why is this here?" (Chapter 21 used bisect to find a regression's commit); a reformatting
commit puts a layer of noise over it. `IncludeBlocks: Preserve` was chosen for the same reason:
Google's regrouping of includes moves lines in files that are otherwise untouched, 75 more lines in
five more files on the same tree.

So `.clang-format` is checked on changed lines only (coding standard rule 1.4, ADR 0027). Git ships
the tool for it: `git clang-format` runs clang-format on the lines that differ between the working
tree, or the staged changes, and a commit. `tools/check_format.py` wraps it as a check
(SRS-BLD-004): with `--staged` it checks what the next commit adds; with two commits it checks the
lines that differ between them; it fails when clang-format would change any of those lines and
prints the diff that would fix them, which `git clang-format` applies. Lines a change does not touch
are not checked, so the code is formatted as it is edited, and a file that is never edited again
keeps its history.

The check runs in two places. The CI job `format` runs it on the lines of the push or the pull
request: the commit before the push and the pushed commit, or the pull request's base and head, with
the last commit alone when a new branch has no "before". That is the gate. The second place is a
pre-commit hook, `tools/hooks/pre-commit`, which finds the same problem a push earlier and checks
three other things on the staged changes (SRS-BLD-005): whitespace errors and conflict markers (`git
diff --cached --check`), ruff on the staged Python files of the analysis package, and an e-mail
address in an added line, other than a placeholder (`example.com`, `example.invalid`) or a no-reply
address. The last one is there because the repository is public: an address committed to it is
published with its history, and a history rewrite to remove it is a change of its own. A hook is
installed per clone (`git config core.hooksPath tools/hooks`), can be skipped with `git commit
--no-verify`, and does nothing on a machine where it is not installed, which is why CI's job is the
gate and the hook is a convenience.

The hook's first day found a defect in itself. Its address pattern matched `+@unittest.skipUnless`
in a diff, a Python decorator on an added line, and refused the commit of Exercise 32.3's test. The
pattern now requires the part before `@` to start with a letter or a digit, and a test commits a
decorator. The test of the hook also had to build its sample address at run time: written as a
literal, the hook refused the commit of its own test.

Both tools are verified the way Chapter 20 verifies tools whose output is evidence of a check.
`tools/test_check_format.py` and `tools/test_pre_commit.py` run them in scratch repositories with
the project's `.clang-format`, and show each check failing on a planted fault and passing on clean
input; an unformatted line in an untouched old file must pass. The gate self-test gained the fault
`format`, an unformatted function added to `crc32.cpp`, which the check must catch for its reason.
clang-format's output differs between major versions, so its version is in the tool list (TL-37,
18.1.3) and the static analysis job checks it.

## When a change to the build breaks something else

Two failures in this chapter came from the build change, not from the code, and both are worth their
problem reports.

**A release tool lost the compiler (MDQ-PR-049).** Moving the compilers into toolchain files changed
where CMake records them. A cache variable set by a preset is in `CMakeCache.txt`; a variable set by
a toolchain file is not. `tools/release_bundle.py` read the compiler's path from the cache to record
its version in the release bundle, and the CI job `reproducible-build` stopped with `KeyError:
'CMAKE_CXX_COMPILER'`. Every local run had passed, because the local build directories had been
configured before the change and their caches still held the old entry. The tool, and the system
test report's script, which read the same entry, now fall back to the value CMake records in the
build tree (`CMakeFiles/<version>/CMakeCXXCompiler.cmake`), and the reproducibility check gives
identical archives from two checkouts again. The lesson is about where a build change is tested: a
change to how a build is configured is verified in a fresh build directory, which is exactly what CI
has and a developer's machine does not.

**A test that depended on the load (MDQ-PR-048).** Running every test of the release build with four
jobs, while the new exercise tests built small projects in parallel, failed Exercise 21.3's
concurrent snapshot test once. Under six busy processes on four CPUs it failed 249 times in 300: its
20,000 snapshots took about a millisecond and were done before its writer thread had recorded
anything. It is the defect of MDQ-PR-028, found in the product's flight recorder test at release
0.4.0, in the exercise's copy of that test, which the search for other instances did not cover. The
writer now counts down a `std::latch` after its first event, and the test passed 300 times under the
same load. CAPA-0001 counts it at the 0.7.0 effectiveness check.

## What this leaves out

C++20 modules change how a build finds dependencies (the build must scan sources to order their
compiles), and CMake supports them with Ninja; MiniDAQ turns the scan off
(`CMAKE_CXX_SCAN_FOR_MODULES OFF`), because it uses no modules and clang-tidy cannot read the scan's
compile commands. Shared libraries and their versioning (`SOVERSION`, run paths, symbol visibility)
matter for a library installed system-wide; the projector is installed as a static library.
Cross-compiling for the acquisition computer is described, not done: the toolchain files are ready
for it, the sysroot is not. A package manager, a compiler cache and a faster linker are each a
reasonable next step with a cost the chapter names. And formatting is one tool of several:
`clang-tidy` (Chapter 7) checks code, `include-what-you-use` could check the includes that Exercise
32.3 trims by hand.

::: box-regulated
- **The build is part of the software's configuration.** IEC 62304 expects the tools and the
  environment that build the software to be identified and controlled. Pinned dependencies, a SOUP
  list that a test keeps in agreement with the pins, toolchain files and presets under version
  control, and a reproducibility check are how MiniDAQ meets that (verify: the standard's clauses on
  configuration management and software release; assumption: confirm with team).
- **Tools in the tool list.** clang-format (TL-37) touches source code and scikit-build-core (TL-38)
  builds a module whose output becomes images; each has a class, a version check where it has one,
  and a test that shows it can fail. A formatting tool's change is reviewed, compiled and tested
  like any other edit.
- **Requirements of the build.** SRS-BLD-001 to SRS-BLD-005 state what the installed package, the
  presets, the wheel, the formatting check and the hook must do, each verified by a test that
  `docs.trace` finds.
- **An interface is a promise.** The installed package's targets, namespace and version
  compatibility are an interface for every project that uses it; a change to them goes through
  change control like a change to a file format.
- **Change records.** CR-0018 records the change and ADR 0027 the decisions, with the alternatives
  that were not taken (a package manager, reformatting the whole tree, a second build for the
  wheel).
:::

::: box-askteam
1. How do other projects use our libraries: an installed package, a copy of the sources, or the
   build tree's paths? Who would notice a copy that keeps an old bug?
2. Which configurations does CI run, and can a developer run exactly one of them with one command?
3. How are third-party libraries pinned, and does a check keep the pins and the SOUP list in
   agreement?
4. Which libraries come from the operating system, and who decides when they are updated?
5. How long does a rebuild take after changing the most included header? Has anyone measured it?
6. Is there a formatting rule, and is it checked? Was the codebase reformatted at once, and what
   happened to `git blame`?
7. Are the pre-commit hooks shared and versioned, or does each developer have their own?
:::

## Exercises {.unnumbered}

**Exercise 32.1 (M): Make a library installable.** *Goal:* turn the library `pulse` into a CMake
package that another project finds with `find_package(pulse 1.2 REQUIRED)` and links as
`pulse::pulse`, from any directory it is installed to. *Starter:*
`exercises/ch32/e1_install/starter/CMakeLists.txt`, which installs the files but no package, with a
source-tree include path and a public build definition. *Acceptance:* `tests/test_install.py`
passes: the configuration, version and targets files are installed, no installed CMake file names
the source or build directory, an installation copied elsewhere is found and the consumer builds
without `PULSE_CHECKED` and prints `area 70 peak 2`, and a request for 1.0 is accepted and one for
2.0 refused. Then answer in `NOTES.md` how the targets file finds its prefix, what changes with a
shared library, and what the configuration file would need for a public dependency. *Time:* 60
minutes.

**Exercise 32.2 (E): One command per configuration.** *Goal:* write the presets of a small project
so that `cmake --workflow --preset dev` and `cmake --workflow --preset asan` each configure, build
and test it. *Starter:* `exercises/ch32/e2_presets/starter/CMakePresets.json`, with two configure
presets, an `asan` one that does not link the sanitizer, and no other presets. *Acceptance:*
`tests/test_presets.py` passes: the `dev` workflow passes both tests, the `asan` workflow builds and
then fails with AddressSanitizer's `heap-buffer-overflow` in `window.cpp`, and each configuration
has build, test and workflow presets. Then fix the defect by hand, explain why the `dev` tests do
not see it, and say why `CMakeUserPresets.json` is not committed. *Time:* 30 minutes.

**Exercise 32.3 (M): A header that costs a rebuild.** *Goal:* make a change to `config.hpp`
recompile only the three sources that use the configuration. *Starter:*
`exercises/ch32/e3_rebuild/starter/src/geometry.hpp`, which includes `config.hpp` and keeps a copy
of the configuration. *Acceptance:* `tests/test_rebuild.py` passes: the program prints 6143.858,
Ninja's dry run after touching `config.hpp` lists `config.cpp`, `geometry.cpp` and `main.cpp` only,
and touching `geometry.hpp` still recompiles the eight rings. Then look at Ninja's recorded
dependencies of one object, compare with the chapter's measurements, and say when a forward
declaration is not enough. *Time:* 30 minutes.

## MiniDAQ milestone: the build as an interface {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ's projector library installs as a CMake package that a test uses from outside,
every configuration is one workflow command, the projector's module builds as a wheel from the same
project, the build's times are measured, and every changed C++ line is checked against
`.clang-format` in CI and in a pre-commit hook. **Start:** tag `ch31`. **End:** tag `ch32`.
:::

1. Write change request CR-0018 and ADR 0027; add SRS-BLD-001 to SRS-BLD-005 (SRS version 21), TL-37
   and TL-38 to the tool list, rule 1.4 to the coding standard (version 5) and the formatting check
   to the development plan (version 11); update the architecture description (version 18) and review
   the threat model (version 6).
2. Install `recon::projector` with an export set, `recon/cmake/reconConfig.cmake.in` and a version
   file in the component `recon_dev`; add `recon/tests/consumer`, `consumer_test.cmake` and the test
   `cmake.consumer`.
3. Add workflow presets for every configuration and `cmake/toolchains/`; add
   `tools/check_presets.py` with its tests and the test `docs.presets`.
4. Add `recon/python/pyproject.toml`, the `recon_python` install rule and the test `recon.wheel`,
   run in the CI job `python`.
5. Add `.clang-format`, `tools/check_format.py`, `tools/hooks/pre-commit`, their tests, the CI job
   `format` and the gate self-test's fault `format`.
6. Add `measurements/ch32/build_times.py` and its results; add Exercises 32.1 to 32.3 with the
   helper `minidaq_cmake_exercise`.

**Definition of done.** `ci/run_all.sh` is green on all six presets; the CI jobs `format` and
`python` pass; `cmake.consumer` and `recon.wheel` pass; the gate self-test catches `format` for its
reason; the reproducibility check gives identical archives; the trace matrix shows SRS-BLD-001 to
SRS-BLD-005 tested; every starter of the chapter fails. Tag `ch32`.

## Check yourself {.unnumbered}

1. What does `PUBLIC` pass on that `PRIVATE` does not, and what does a private dependency of a
   static library still pass on?
2. Why is MiniDAQ's warnings target an `INTERFACE` library linked privately, and what would
   `add_compile_options` at the top level have done to GoogleTest?
3. Why is `if($<CONFIG:Debug>)` always true?
4. What does a workflow preset add to configure, build and test presets, and what keeps every
   configuration's workflow in place?
5. Why move the compilers into toolchain files when the native build is unchanged? What did the move
   break, and why did no local run see it?
6. Which two errors does CMake report when the projector is exported with the old include path and
   the warnings target? What does each prevent?
7. What does `find_dependency(Threads)` do in `reconConfig.cmake`, and why must it come before the
   targets file?
8. Why `SameMinorVersion` before 1.0?
9. Why does the test of the package install into an empty prefix and build a separate project?
10. What makes a pin, and why is a tag not one? Which dependency is found instead of fetched, and
    why?
11. What would a package manager add, and why does MiniDAQ not use one?
12. Why does the wheel come from the main CMake project, and what does `SKBUILD` do there?
13. Why did the first version of the wheel's test pass for the wrong reason?
14. Touching `crc32.cpp` compiles one file and runs 129 commands. What are the other 128?
15. How does Ninja know which files include a header?
16. Why check formatting only on changed lines? What would reformatting every file have cost?
17. Which checks does the pre-commit hook make, and why is it not the gate?

## Summary {.unnumbered}

- A target's usage requirements are what it passes on: `PRIVATE` for its own sources, `INTERFACE`
  for its users, `PUBLIC` for both. Private unless a header needs it; build settings such as
  warnings live in `INTERFACE` libraries linked privately.
- Generator expressions are evaluated at generation, per configuration; `BUILD_INTERFACE` and
  `INSTALL_INTERFACE` give a target one value in the build and another once installed.
- Every configuration has a workflow preset, the whole gate in one command; `docs.presets` keeps the
  presets and the CI matrix consistent. Compilers come from toolchain files, where a cross build
  adds its system, sysroot and search modes.
- `recon::projector` installs as a CMake package (export set, configuration file with
  `find_dependency`, `SameMinorVersion` version file, component `recon_dev`); `cmake.consumer`
  installs it into an empty prefix and builds and runs a project that uses it.
- Dependencies are pinned by commit or archive hash, shared in one download directory, checked
  against the SOUP list and scanned through the SBOM; platform libraries are found. No package
  manager, for four reviewed dependencies.
- scikit-build-core builds the projector's wheel from the main project, one target and one
  component; `recon.wheel` tests the installed module with nothing of the build tree on the path.
- A clean build takes 156.6 s; touching a header included by most of the code costs 84.5 s, a leaf
  source 1.6 s. Includes in headers are paid by every includer; forward declarations and smaller
  headers cut the cost.
- `.clang-format` is checked on changed lines, by a pre-commit hook and the CI job `format`;
  reformatting the tree would have rewritten 1,883 lines in 308 files and buried their history.
- A change to the build is tested in a fresh build directory (MDQ-PR-049), and a test that starts a
  thread waits for it to start (MDQ-PR-048).

## Further reading {.unnumbered}

- The CMake documentation: `cmake-buildsystem(7)` for targets and usage requirements,
  `cmake-generator-expressions(7)`, `cmake-presets(7)`, `cmake-toolchains(7)`, `cmake-packages(7)`,
  and the modules `CMakePackageConfigHelpers`, `CMakeFindDependencyMacro` and `FetchContent`.
- C. Scott, *Professional CMake: A Practical Guide*, Crascit, updated with each CMake release
  (verify the current edition).
- J. Lakos, *Large-Scale C++ Software Design*, Addison-Wesley, 1996, on physical design: the
  dependencies between files and what they cost a build.
- The scikit-build-core documentation, on the `[tool.scikit-build]` settings, and the Python
  Packaging User Guide, on wheels and platform tags; PEP 600 for `manylinux` tags.
- The clang-format documentation (style options) and the `git clang-format` help; `githooks(5)` for
  Git's hooks and `core.hooksPath`.
- ADR 0027 and CR-0018 in the repository: the decisions and the change record.
