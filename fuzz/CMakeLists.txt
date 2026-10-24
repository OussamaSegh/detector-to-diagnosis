# Fuzz targets (Chapter 7). Built with -DMINIDAQ_BUILD_FUZZERS=ON and Clang (preset `fuzz`).
# Each target also becomes a short CTest smoke run over its seed corpus (label "fuzz");
# real fuzzing campaigns run for hours, see fuzz/README.md.
set(MINIDAQ_FUZZ_SMOKE_SECONDS 20 CACHE STRING "Seconds per fuzz target in the CTest smoke run")

function(minidaq_fuzzer name)
  cmake_parse_arguments(FZ "" "" "LIBS" ${ARGN})
  add_executable(${name} ${name}.cpp)
  target_link_libraries(${name} PRIVATE ${FZ_LIBS} minidaq::warnings)
  target_link_options(${name} PRIVATE -fsanitize=fuzzer)
  string(REPLACE "fuzz_" "" _corpus ${name})
  set(_seeds ${CMAKE_CURRENT_SOURCE_DIR}/corpus/${_corpus})
  set(_work ${CMAKE_CURRENT_BINARY_DIR}/corpus-${_corpus})
  add_test(NAME fuzz.${_corpus}
           COMMAND ${CMAKE_COMMAND} -E env ASAN_OPTIONS=detect_leaks=1
                   $<TARGET_FILE:${name}> -max_total_time=${MINIDAQ_FUZZ_SMOKE_SECONDS} -timeout=5
                   -rss_limit_mb=2048 -print_final_stats=1 ${_work} ${_seeds})
  set_tests_properties(fuzz.${_corpus} PROPERTIES LABELS "fuzz" TIMEOUT 300)
  file(MAKE_DIRECTORY ${_work})
endfunction()

minidaq_fuzzer(fuzz_decoder LIBS minidaq::core)
minidaq_fuzzer(fuzz_raw16 LIBS minidaq::core)
minidaq_fuzzer(fuzz_packet LIBS minidaq::core)
minidaq_fuzzer(fuzz_config LIBS minidaq::control)
minidaq_fuzzer(fuzz_protocol LIBS minidaq::control)
minidaq_fuzzer(fuzz_sorter LIBS minidaq::core)
