# The reconstruction's projector in C++ (Chapter 29, ADR 0024): part of the tool tools/recon
# (TL-31), not of the shipped programs. The library is plain C++20; the Python module wraps it.
add_library(recon_projector src/joseph.cpp)
add_library(recon::projector ALIAS recon_projector)
target_include_directories(recon_projector PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>)
target_compile_features(recon_projector PUBLIC cxx_std_20)
find_package(Threads REQUIRED)
target_link_libraries(recon_projector PUBLIC Threads::Threads PRIVATE minidaq::warnings)
# The module is a shared object loaded by Python, so the library must be position independent.
set_target_properties(recon_projector PROPERTIES POSITION_INDEPENDENT_CODE ON)

if(MINIDAQ_BUILD_RECON_PYTHON)
  pybind11_add_module(recon_cpp python/recon_cpp.cpp)
  target_link_libraries(recon_cpp PRIVATE recon::projector minidaq::warnings)
endif()

# Hardening (cmake/Hardening.cmake) compiles everything -fPIE and links with -pie, for programs.
# Code for a shared object needs -fPIC (a PIE's thread-local and global accesses cannot be
# relocated in one), and -pie has no meaning for it. -fPIC last wins over -fPIE.
if(MINIDAQ_HARDENING)
  target_compile_options(recon_projector PRIVATE -fPIC)
  if(TARGET recon_cpp)
    target_compile_options(recon_cpp PRIVATE -fPIC)
    get_target_property(_recon_link recon_cpp LINK_OPTIONS)
    if(_recon_link)
      list(REMOVE_ITEM _recon_link -pie)
      set_target_properties(recon_cpp PROPERTIES LINK_OPTIONS "${_recon_link}")
    endif()
  endif()
endif()

if(MINIDAQ_BUILD_TESTS)
  add_executable(recon_tests tests/test_joseph.cpp)
  target_link_libraries(recon_tests PRIVATE recon::projector GTest::gtest_main minidaq::warnings)
  gtest_discover_tests(recon_tests PROPERTIES LABELS "unit")
  if(MINIDAQ_BUILD_RECON_PYTHON)
    # The Python tests of tools/recon, run against both projectors: numpy and recon_cpp.
    add_test(NAME tools.recon_cpp
             COMMAND ${Python3_EXECUTABLE} -B ${PROJECT_SOURCE_DIR}/tools/test_recon_cpp.py)
    set_tests_properties(tools.recon_cpp PROPERTIES LABELS "unit" TIMEOUT 300
      ENVIRONMENT "MINIDAQ_RECON_CPP=$<TARGET_FILE_DIR:recon_cpp>")
  endif()
endif()
