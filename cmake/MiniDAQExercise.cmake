# minidaq_exercise(<dir> [LIBS <targets>...] [NO_GTEST_MAIN])
# Builds <dir>/starter and/or <dir>/solution together with <dir>/tests.
function(minidaq_exercise dir)
  cmake_parse_arguments(EX "NO_GTEST_MAIN" "" "LIBS" ${ARGN})
  get_filename_component(_abs ${dir} ABSOLUTE)
  get_filename_component(_name ${_abs} NAME)
  get_filename_component(_chdir ${_abs} DIRECTORY)
  get_filename_component(_ch ${_chdir} NAME)
  file(GLOB _tests CONFIGURE_DEPENDS ${_abs}/tests/*.cpp)

  set(_variants)
  if(MINIDAQ_BUILD_EXERCISES)
    list(APPEND _variants solution)
  endif()
  if(MINIDAQ_BUILD_STARTERS)
    list(APPEND _variants starter)
  endif()

  foreach(_v IN LISTS _variants)
    set(_t ${_ch}_${_name}_${_v})
    file(GLOB _srcs CONFIGURE_DEPENDS ${_abs}/${_v}/*.cpp)
    add_executable(${_t} ${_srcs} ${_tests})
    target_include_directories(${_t} PRIVATE ${_abs}/${_v})
    target_link_libraries(${_t} PRIVATE minidaq::core minidaq::warnings ${EX_LIBS})
    if(EX_NO_GTEST_MAIN)
      target_link_libraries(${_t} PRIVATE GTest::gtest GTest::gmock)
    else()
      target_link_libraries(${_t} PRIVATE GTest::gtest_main GTest::gmock)
    endif()
    if(_v STREQUAL "starter")
      # Starters intentionally contain unused parameters and TODO stubs.
      target_compile_options(${_t} PRIVATE -Wno-error)
    endif()
    gtest_discover_tests(${_t}
      TEST_PREFIX "${_ch}/${_name}/${_v}/"
      PROPERTIES LABELS ${_v}
      DISCOVERY_TIMEOUT 30)
  endforeach()
endfunction()
