# Exercise 32.1 (M): Make a library installable

**Goal.** Turn the library `pulse` into a CMake package that another project finds with
`find_package(pulse 1.2 REQUIRED)` and links as `pulse::pulse`, from any directory it is
installed to.

**Time.** 60 minutes.

**Starter.** `starter/CMakeLists.txt` builds the library and installs its archive and headers.
Its include directory is a path of the source tree, its build definition `PULSE_CHECKED` is
public, and it installs no package files, so `find_package(pulse)` fails.

**Acceptance** (`tests/test_install.py`, which builds the project, installs it and builds
`tests/consumer` against it):
- `pulseConfig.cmake`, `pulseConfigVersion.cmake` and `pulseTargets.cmake` are installed.
- No installed CMake file names the source or the build directory.
- An installation copied to another directory is found, the consumer builds against it without
  `PULSE_CHECKED` and prints `area 70 peak 2`.
- A request for version 1.0 finds 1.2; a request for 2.0 does not.

**Then, by hand.**
1. Look at the installed `pulseTargets.cmake`. How does it find the prefix it was installed to?
2. Make `pulse` a shared library (`-DBUILD_SHARED_LIBS=ON`). What else is installed, and does the
   consumer still run from the copied installation? Write down why in `NOTES.md`.
3. If `pulse` needed `Threads::Threads` publicly, what would `pulseConfig.cmake` have to do?

**Hints.** `$<BUILD_INTERFACE:...>` and `$<INSTALL_INTERFACE:...>`; `install(TARGETS ... EXPORT)`
and `install(EXPORT ... NAMESPACE pulse::)`; `CMakePackageConfigHelpers` has
`configure_package_config_file` and `write_basic_package_version_file`.
