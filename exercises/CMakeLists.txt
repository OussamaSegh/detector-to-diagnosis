# Exercises. Every exercise directory has the same layout:
#   README.md   goal, time estimate, acceptance criteria
#   tests/      acceptance tests (shared by starter and solution)
#   starter/    code with TODOs; its tests FAIL until you finish it
#   solution/   reference implementation plus NOTES.md (design choices)
# Solutions are built and tested by default. Configure with
# -DMINIDAQ_BUILD_STARTERS=ON to build your own work against the same tests:
#   ctest --preset debug -L starter -R ch03
include(MiniDAQExercise)

file(GLOB _chapters LIST_DIRECTORIES true RELATIVE ${CMAKE_CURRENT_SOURCE_DIR} ch[0-9][0-9])
foreach(_ch IN LISTS _chapters)
  if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/${_ch}/CMakeLists.txt)
    add_subdirectory(${_ch})
  endif()
endforeach()
