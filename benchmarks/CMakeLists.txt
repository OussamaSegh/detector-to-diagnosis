# Micro-benchmarks (Chapters 2, 3, 5, 10). Run them from a Release build:
#   cmake --preset release && cmake --build --preset release
#   build/release/benchmarks/bm_layout --benchmark_repetitions=5
# Every published number in the book states machine, compiler and flags.
function(minidaq_benchmark name)
  add_executable(${name} ${name}.cpp)
  target_link_libraries(${name} PRIVATE minidaq::core minidaq::warnings benchmark::benchmark_main ${ARGN})
endfunction()

minidaq_benchmark(bm_layout)
minidaq_benchmark(bm_alloc)
minidaq_benchmark(bm_false_sharing)
minidaq_benchmark(bm_decode)
minidaq_benchmark(bm_latency)
minidaq_benchmark(bm_spsc)
minidaq_benchmark(bm_pipeline)
minidaq_benchmark(bm_histogram)
minidaq_benchmark(bm_energy_filter)
minidaq_benchmark(bm_sort)
minidaq_benchmark(bm_sorter)
