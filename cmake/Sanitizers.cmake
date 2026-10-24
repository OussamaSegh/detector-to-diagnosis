# Sanitizer builds (Chapter 1, Chapter 3). Selected by the presets asan-ubsan and tsan.
# Sanitizer flags are applied globally on purpose: every object in the process,
# including GoogleTest, must be instrumented or TSan reports false positives.
if(MINIDAQ_SANITIZERS)
  if("thread" IN_LIST MINIDAQ_SANITIZERS AND "address" IN_LIST MINIDAQ_SANITIZERS)
    message(FATAL_ERROR "ThreadSanitizer cannot be combined with AddressSanitizer")
  endif()
  list(JOIN MINIDAQ_SANITIZERS "," _san)
  message(STATUS "MiniDAQ: sanitizers enabled: ${_san}")
  add_compile_options(-fsanitize=${_san} -fno-omit-frame-pointer -fno-sanitize-recover=all)
  add_link_options(-fsanitize=${_san})
endif()
