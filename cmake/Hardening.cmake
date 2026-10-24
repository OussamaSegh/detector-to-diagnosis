# Compiler and linker hardening (Chapter 7). Selected by MINIDAQ_HARDENING
# (preset `hardened`); applied to every target, because an unhardened object
# linked into a hardened program is the weak point.
#
# What each flag buys (and costs) is in Chapter 7 and ADR 0008. Distribution
# compilers may enable some of these by default; stating them here makes the
# build independent of that, and tools/check_hardening.py checks the result.
if(MINIDAQ_HARDENING)
  if(MINIDAQ_SANITIZERS)
    message(FATAL_ERROR "MINIDAQ_HARDENING is for release builds; do not combine it with sanitizers")
  endif()
  if(NOT CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    message(FATAL_ERROR "MINIDAQ_HARDENING supports GCC and Clang")
  endif()
  message(STATUS "MiniDAQ: hardening enabled")
  # [snippet:flags]
  add_compile_options(
    -fstack-protector-strong       # canary in functions with arrays or address-taken locals
    -fstack-clash-protection       # probe large stack allocations page by page
    -D_GLIBCXX_ASSERTIONS          # bounds checks in std::vector, std::span, std::array ...
    -fPIE)
  # _FORTIFY_SOURCE needs optimization; -U first because some distributions
  # predefine it, and a redefinition would be a warning (an error here).
  add_compile_options($<$<NOT:$<CONFIG:Debug>>:-U_FORTIFY_SOURCE> $<$<NOT:$<CONFIG:Debug>>:-D_FORTIFY_SOURCE=3>)
  if(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|AMD64")
    add_compile_options(-fcf-protection=full)  # CET: indirect-branch tracking and shadow stack
  endif()
  add_link_options(-pie -Wl,-z,relro -Wl,-z,now -Wl,-z,noexecstack)
  # [/snippet:flags]
endif()
