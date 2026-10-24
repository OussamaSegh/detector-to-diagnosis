# Warning policy shared by every MiniDAQ target (Chapter 1, Chapter 7).
# Applied through an INTERFACE target so the flags never leak into third-party code.
add_library(minidaq_warnings INTERFACE)
add_library(minidaq::warnings ALIAS minidaq_warnings)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(minidaq_warnings INTERFACE
    -Wall -Wextra -Wpedantic
    -Wshadow -Wconversion -Wsign-conversion
    -Wold-style-cast -Wcast-align
    -Wdouble-promotion -Wformat=2 -Wimplicit-fallthrough
    -Wnon-virtual-dtor -Woverloaded-virtual)
  if(MINIDAQ_WARNINGS_AS_ERRORS)
    target_compile_options(minidaq_warnings INTERFACE -Werror)
  endif()
elseif(MSVC)
  target_compile_options(minidaq_warnings INTERFACE /W4 /permissive-)
  if(MINIDAQ_WARNINGS_AS_ERRORS)
    target_compile_options(minidaq_warnings INTERFACE /WX)
  endif()
endif()
