# Exercise 32.1: notes

The starter makes three mistakes, and each one fails a test:

1. Its include directory is `${CMAKE_CURRENT_SOURCE_DIR}/include`, an absolute path of the source
   tree. `install(EXPORT)` refuses to export it ("includes non-prefix path"), and if it did, every
   user's build would depend on a directory that exists only on the machine that built the
   library. The generator expressions give each context its own path: the source tree while
   building, `include` under whatever prefix the package lands in once installed.
2. `PULSE_CHECKED` is public, so every user compiles with it. Here it only turns on the library's
   own assertions, but a definition that changes a type's layout in a header would give the
   library and its users two different types under one name, an ODR violation that the linker
   does not report. The consumer refuses it with `#error`.
3. It installs no package. `find_package(pulse)` in config mode looks for `pulseConfig.cmake`
   (or `pulse-config.cmake`) under the prefixes it searches; without it the consumer stops at
   configure time.

The version file uses `SameMajorVersion`: 1.2 satisfies a request for 1.0, and not one for 2.0.
`AnyNewerVersion` would accept 2.0 as well, which promises compatibility across a major version.

By hand:

1. `pulseTargets.cmake` computes `_IMPORT_PREFIX` from its own location
   (`${CMAKE_CURRENT_LIST_FILE}`, then up as many directories as it is installed below the
   prefix), and every path in it is relative to that. This is why the copy works.
2. With `BUILD_SHARED_LIBS=ON` the library is `libpulse.so` and the consumer records its path in
   the executable's run path at build time, so it runs from the copied installation. A program
   installed with the library would need `CMAKE_INSTALL_RPATH` (for example `$ORIGIN/../lib`)
   instead of the build-time path.
3. Call `include(CMakeFindDependencyMacro)` and `find_dependency(Threads)` before including the
   targets file: the exported target names `Threads::Threads`, which must exist in the user's
   project when the targets file is read.
