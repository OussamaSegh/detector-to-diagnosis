# cmake -DEXE=<gtest binary> -DMIN=<n> -P CountTests.cmake
# Fails unless the binary has at least MIN test cases (Chapter 18 exercises).
execute_process(COMMAND ${EXE} --gtest_list_tests OUTPUT_VARIABLE _list RESULT_VARIABLE _rc)
if(NOT _rc EQUAL 0)
  message(FATAL_ERROR "${EXE} --gtest_list_tests failed")
endif()
string(REGEX MATCHALL "\n  [^\n]+" _cases "${_list}")
list(LENGTH _cases _n)
if(_n LESS MIN)
  message(FATAL_ERROR "${_n} test cases, at least ${MIN} required")
endif()
message(STATUS "${_n} test cases")
