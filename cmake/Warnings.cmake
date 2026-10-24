# Warning policy shared by every MiniDAQ target (Chapter 1, Chapter 7).
# Applied through INTERFACE targets so the flags never leak into third-party code.
#   minidaq::warnings          the full set, as errors (all MiniDAQ code)
#   minidaq::warnings_no_error the same set as plain warnings (exercise starters,
#                              which contain TODO stubs with unused parameters)
add_library(minidaq_warnings_no_error INTERFACE)
add_library(minidaq::warnings_no_error ALIAS minidaq_warnings_no_error)
add_library(minidaq_warnings INTERFACE)
add_library(minidaq::warnings ALIAS minidaq_warnings)
target_link_libraries(minidaq_warnings INTERFACE minidaq_warnings_no_error)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(minidaq_warnings_no_error INTERFACE
    -Wall -Wextra -Wpedantic
    -Wshadow -Wconversion -Wsign-conversion
    -Wold-style-cast -Wcast-align
    -Wdouble-promotion -Wformat=2 -Wimplicit-fallthrough
    -Wnon-virtual-dtor -Woverloaded-virtual)
  if(MINIDAQ_WARNINGS_AS_ERRORS)
    target_compile_options(minidaq_warnings INTERFACE -Werror)
  endif()
elseif(MSVC)
  target_compile_options(minidaq_warnings_no_error INTERFACE /W4 /permissive-)
  if(MINIDAQ_WARNINGS_AS_ERRORS)
    target_compile_options(minidaq_warnings INTERFACE /WX)
  endif()
endif()
