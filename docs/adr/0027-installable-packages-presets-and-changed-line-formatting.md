# 0027. Installable CMake packages, a workflow preset per configuration, a wheel from the same project, and formatting checked on changed lines

Date: 2026-11-04
Status: Accepted

## Context

By the end of Part VI, MiniDAQ's one CMake project built a C++ server, its tests, a reconstruction
library with a Python module, the exercises and the benchmarks. It worked, in one way: from this
repository, on a machine set up as the CI runners are. Four questions had no answer:

- how another project uses one of MiniDAQ's libraries (the physics group's own C++ tools wanted the
  projector) without copying its sources or its build tree's paths;
- how a developer runs exactly what CI runs for one configuration, with one command;
- how the projector's Python module is installed on a machine that has no MiniDAQ build, without a
  second build system that describes the same module again;
- how the code's formatting is kept consistent, when nothing had checked it for 31 chapters.

## Options

For using a library from another project: copy its sources (a fork that drifts); add the whole
MiniDAQ tree with `add_subdirectory` or FetchContent (every MiniDAQ option and target enters the
user's project); or install the library with a CMake package that `find_package` reads.

For the configurations: keep the documented `cmake --preset X && cmake --build --preset X && ctest
--preset X`; a script per configuration (`ci/run_all.sh` already loops over them); or workflow
presets (presets file version 6), which name the three steps as one.

For the Python module: setuptools with a `build_ext` that compiles the module again (a second
description of the sources, flags and dependencies); or scikit-build-core, which runs the existing
CMake project and installs one component into the wheel.

For dependencies: FetchContent pinned by commit or archive hash, as since Chapter 1; a package
manager (Conan or vcpkg). Conan was proposed in Chapter 31 and not approved.

For formatting: no rule (the status quo); reformat every file once and then check every file; or
check only the lines each change touches.

## Decision

- **Installed package.** The projector library installs, in the component `recon_dev`, with an
  export set under the namespace `recon::`, a package configuration file that finds its public
  dependency (`Threads`) with `find_dependency`, and a version file with `SameMinorVersion`
  compatibility while MiniDAQ is before 1.0. Include directories are given per context
  (`BUILD_INTERFACE` and `INSTALL_INTERFACE`); the warnings target, how MiniDAQ builds its code, is
  linked only in the build interface. The test `cmake.consumer` installs into an empty prefix,
  checks that no installed CMake file names the build or source tree, and builds and runs a
  project that uses the library through `find_package` (SRS-BLD-001).
- **Presets.** Every configuration has a build, a test and a workflow preset of its name;
  `cmake --workflow --preset NAME` is the gate of that configuration. Compilers are chosen by
  toolchain files (`cmake/toolchains/`), not cache variables, so that a cross toolchain is a new
  file. `tools/check_presets.py` (test `docs.presets`) keeps the presets and the CI matrix
  consistent (SRS-BLD-002).
- **Wheel.** `recon/python/pyproject.toml` builds the module with scikit-build-core from the main
  project, with everything but the module switched off, the target `recon_cpp` and the component
  `recon_python` (SKBUILD is set only in a wheel build). The test `recon.wheel` installs the wheel
  alone and runs the projector's tests against it (SRS-BLD-003).
- **Dependencies.** FetchContent with exact pins stays, checked against the SOUP list by
  `docs.soup`; platform libraries (OpenSSL) are found. No package manager.
- **Formatting.** `.clang-format` (Google's style at 100 columns, pointers to the left, include
  blocks preserved) is checked only on the lines a change adds or edits: `tools/check_format.py`
  in a pre-commit hook and in the CI job `format` (SRS-BLD-004). The hook also refuses whitespace
  errors and an e-mail address that is not a placeholder (SRS-BLD-005). Coding standard rule 1.4.

## Consequences

### Positive

- Another CMake project uses the projector with two lines, from any prefix, and the test proves it
  on every build. The two mistakes the test was written against, the source tree's include path
  and the warnings target in the export, are refused by CMake at configure time.
- A developer reproduces a CI job with one command; a configuration without its workflow, or a CI
  matrix entry without its preset, fails a test.
- The wheel and the build tree's module come from the same CMake code, so they cannot drift.
- Reformatting the whole tree would have rewritten 1,881 lines in 308 of 580 C++ files
  (`.clang-format`, measured before it was committed) and put a format commit on top of the history
  of most lines. Checking changed lines formats the code as it is edited and leaves history intact.

### Negative

- The installed package is a promise: its targets, namespace and version compatibility are an
  interface, and a change to them is a change for every user.
- The wheel is built for the build machine's Python and platform (`linux_x86_64`), not as a
  portable `manylinux` wheel; distributing it to other machines would need that step.
- The tree stays mixed: old lines in their authors' style, new lines in clang-format's, until each
  is touched. A diff that touches a line next to old ones can show more changes than its author
  made.
- The pre-commit hook works only where it is installed (`git config core.hooksPath tools/hooks`);
  CI's job is the gate, the hook is a convenience that finds the problem a push earlier.
- clang-format's output differs between major versions, so its version is pinned in the tool list
  (TL-37) and an upgrade is a change.
