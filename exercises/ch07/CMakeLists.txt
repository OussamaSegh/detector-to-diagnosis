minidaq_exercise(e1_tidy_zero)
minidaq_exercise(e2_fuzz_packets)
minidaq_python_exercise(e3_sbom_diff)
minidaq_exercise(e4_untrusted_path)
minidaq_exercise(e5_strict_duration)

# Exercise 7.1: clang-tidy must report nothing for the variant.
find_package(Python3 COMPONENTS Interpreter)
foreach(_v solution starter)
  if((_v STREQUAL "solution" AND MINIDAQ_BUILD_EXERCISES) OR (_v STREQUAL "starter" AND MINIDAQ_BUILD_STARTERS))
    if(Python3_Interpreter_FOUND)
      add_test(NAME ch07/e1_tidy_zero/${_v}/clang-tidy
               COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/e1_tidy_zero/tests/tidy_clean.py ${_v})
      set_tests_properties(ch07/e1_tidy_zero/${_v}/clang-tidy PROPERTIES LABELS ${_v} SKIP_RETURN_CODE 77 TIMEOUT 300)
    endif()
    # Exercise 7.2: the fuzz target, with a smoke run over the seed corpus.
    if(MINIDAQ_BUILD_FUZZERS)
      set(_d ${CMAKE_CURRENT_SOURCE_DIR}/e2_fuzz_packets/${_v})
      add_executable(ch07_fuzz_packet_${_v} ${_d}/fuzz/fuzz_packet.cpp ${_d}/packet.cpp)
      target_include_directories(ch07_fuzz_packet_${_v} PRIVATE ${_d})
      target_link_libraries(ch07_fuzz_packet_${_v} PRIVATE minidaq::core)
      target_link_options(ch07_fuzz_packet_${_v} PRIVATE -fsanitize=fuzzer)
      set(_work ${CMAKE_CURRENT_BINARY_DIR}/fuzz-packet-${_v})
      file(MAKE_DIRECTORY ${_work})
      add_test(NAME ch07/e2_fuzz_packets/${_v}/fuzz
               COMMAND ch07_fuzz_packet_${_v} -max_total_time=${MINIDAQ_FUZZ_SMOKE_SECONDS} -timeout=5
                       -artifact_prefix=${_work}/ ${_work} ${CMAKE_CURRENT_SOURCE_DIR}/e2_fuzz_packets/tests/corpus)
      set_tests_properties(ch07/e2_fuzz_packets/${_v}/fuzz PROPERTIES LABELS "${_v};fuzz" TIMEOUT 300)
    endif()
  endif()
endforeach()
