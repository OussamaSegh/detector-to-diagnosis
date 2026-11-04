# The reconstruction's projector in C++ (Chapter 29, ADR 0024): part of the tool tools/recon
# (TL-31), not of the shipped programs. The library is plain C++20; the Python module wraps it.
add_library(recon_projector src/joseph.cpp)
add_library(recon::projector ALIAS recon_projector)
# [snippet:usage]
# The headers are found in the source tree while building, and under the install prefix's
# include/ once installed: the two paths differ, so each is given for its own context.
target_include_directories(recon_projector PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)
target_compile_features(recon_projector PUBLIC cxx_std_20)
find_package(Threads REQUIRED)
# The warnings are how MiniDAQ builds its code, not something a user of the library inherits:
# BUILD_INTERFACE keeps them out of the exported target (a static library's private links are
# exported as link-only dependencies, and minidaq::warnings is not installed).
target_link_libraries(recon_projector PUBLIC Threads::Threads
                                      PRIVATE $<BUILD_INTERFACE:minidaq::warnings>)
set_target_properties(recon_projector PROPERTIES EXPORT_NAME projector)
# [/snippet:usage]
# The module is a shared object loaded by Python, so the library must be position independent.
set_target_properties(recon_projector PROPERTIES POSITION_INDEPENDENT_CODE ON)

if(MINIDAQ_BUILD_RECON_PYTHON)
  pybind11_add_module(recon_cpp python/recon_cpp.cpp)
  target_link_libraries(recon_cpp PRIVATE recon::projector minidaq::warnings)
  # Chapter 32: scikit-build-core (recon/python/pyproject.toml) sets SKBUILD and installs this
  # component at the root of the wheel's site-packages.
  if(SKBUILD)
    install(TARGETS recon_cpp LIBRARY DESTINATION . COMPONENT recon_python)
  endif()
endif()

# Chapter 32: the projector library is installed as a CMake package, `find_package(recon)`
# giving recon::projector, so that another project (a 3D reconstruction, a test bench) can use
# it without copying the source. tests/consumer is such a project, built by the test
# cmake.consumer against an installed copy.
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
# [snippet:install]
install(TARGETS recon_projector EXPORT reconTargets
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR} COMPONENT recon_dev)
install(DIRECTORY include/recon DESTINATION ${CMAKE_INSTALL_INCLUDEDIR} COMPONENT recon_dev)
install(EXPORT reconTargets NAMESPACE recon:: DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/recon
        COMPONENT recon_dev)
configure_package_config_file(cmake/reconConfig.cmake.in
  ${CMAKE_CURRENT_BINARY_DIR}/reconConfig.cmake
  INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/recon)
write_basic_package_version_file(${CMAKE_CURRENT_BINARY_DIR}/reconConfigVersion.cmake
  VERSION ${PROJECT_VERSION} COMPATIBILITY SameMinorVersion)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/reconConfig.cmake
              ${CMAKE_CURRENT_BINARY_DIR}/reconConfigVersion.cmake
        DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/recon COMPONENT recon_dev)
# [/snippet:install]

# Code for the module, a shared object, is built without the hardened preset's -fPIE and -pie.
minidaq_as_shared_object(recon_projector)
if(TARGET recon_cpp)
  minidaq_as_shared_object(recon_cpp)
endif()

if(MINIDAQ_BUILD_TESTS)
  # Not with sanitizers or fuzzing, whose flags are directory options the consumer would not
  # have. The flags of the build (coverage's, for one) are passed on.
  find_package(Python3 COMPONENTS Interpreter)
  if(NOT MINIDAQ_SANITIZERS AND NOT MINIDAQ_BUILD_FUZZERS AND Python3_Interpreter_FOUND)
    add_test(NAME cmake.consumer
             COMMAND ${Python3_EXECUTABLE} -B ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_consumer.py
                     ${CMAKE_COMMAND} ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
                     ${CMAKE_CURRENT_BINARY_DIR}/consumer_test ${CMAKE_GENERATOR}
                     ${CMAKE_CXX_COMPILER} "${CMAKE_CXX_FLAGS}" "${CMAKE_EXE_LINKER_FLAGS}")
    set_tests_properties(cmake.consumer PROPERTIES LABELS "unit" TIMEOUT 300)
  endif()
  add_executable(recon_tests tests/test_joseph.cpp)
  target_link_libraries(recon_tests PRIVATE recon::projector GTest::gtest_main minidaq::warnings)
  gtest_discover_tests(recon_tests PROPERTIES LABELS "unit")
  if(MINIDAQ_BUILD_RECON_PYTHON)
    # The Python tests of tools/recon, run against both projectors: numpy and recon_cpp.
    add_test(NAME tools.recon_cpp
             COMMAND ${Python3_EXECUTABLE} -B ${PROJECT_SOURCE_DIR}/tools/test_recon_cpp.py)
    set_tests_properties(tools.recon_cpp PROPERTIES LABELS "unit" TIMEOUT 300
      ENVIRONMENT "MINIDAQ_RECON_CPP=$<TARGET_FILE_DIR:recon_cpp>")
    # Chapter 32: the same module as a pip wheel, built by scikit-build-core from this project.
    add_test(NAME recon.wheel
             COMMAND ${Python3_EXECUTABLE} -B ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_wheel.py
                     ${PROJECT_SOURCE_DIR} ${CMAKE_CURRENT_BINARY_DIR}/wheel_test
                     ${FETCHCONTENT_BASE_DIR})
    set_tests_properties(recon.wheel PROPERTIES LABELS "unit" TIMEOUT 900 SKIP_RETURN_CODE 77)
  endif()
endif()
