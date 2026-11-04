# SPDX-License-Identifier: MIT
# Run by recon/tests/test_consumer.py (the test cmake.consumer, Chapter 32): install the
# projector library from this build into an empty prefix, check that the installed files name no
# path of the build or the source, then configure, build and run a project that uses it through
# find_package.
#   cmake -DBUILD_DIR=... -DSOURCE_DIR=... -DWORK_DIR=... -DGENERATOR=... -DCXX=... -P consumer_test.cmake
foreach(v BUILD_DIR SOURCE_DIR WORK_DIR GENERATOR CXX)
  if(NOT DEFINED ${v})
    message(FATAL_ERROR "consumer_test.cmake needs -D${v}=...")
  endif()
endforeach()
set(prefix ${WORK_DIR}/prefix)
# The consumer asks for the minor version of this build: under SameMinorVersion, a fixed number
# in its find_package would fail at the next VERSION bump (0.7 against 0.8.0-dev), a test defect.
file(READ ${SOURCE_DIR}/VERSION version)
string(REGEX MATCH "^[0-9]+\\.[0-9]+" minor "${version}")
set(consumer_build ${WORK_DIR}/build)
file(REMOVE_RECURSE ${WORK_DIR})

function(run)
  execute_process(COMMAND ${ARGN} RESULT_VARIABLE rc OUTPUT_VARIABLE out ERROR_VARIABLE err)
  if(NOT rc EQUAL 0)
    message(FATAL_ERROR "failed (${rc}): ${ARGN}\n${out}\n${err}")
  endif()
  set(last_output "${out}" PARENT_SCOPE)
endfunction()

# [snippet:test]
run(${CMAKE_COMMAND} --install ${BUILD_DIR} --component recon_dev --prefix ${prefix})
file(GLOB_RECURSE installed RELATIVE ${prefix} ${prefix}/*)
message(STATUS "installed: ${installed}")
foreach(f IN LISTS installed)
  if(f MATCHES "\\.cmake$")
    file(READ ${prefix}/${f} text)
    foreach(dir ${BUILD_DIR} ${SOURCE_DIR})
      string(FIND "${text}" "${dir}" at)
      if(NOT at EQUAL -1)
        message(FATAL_ERROR "${f} names ${dir}: the installed package depends on this machine")
      endif()
    endforeach()
  endif()
endforeach()
run(${CMAKE_COMMAND} -S ${SOURCE_DIR}/recon/tests/consumer -B ${consumer_build} -G ${GENERATOR}
    -DCMAKE_CXX_COMPILER=${CXX} -DCMAKE_PREFIX_PATH=${prefix} -DCMAKE_BUILD_TYPE=Release
    -DRECON_VERSION=${minor}
    "-DCMAKE_CXX_FLAGS=${CXX_FLAGS}" "-DCMAKE_EXE_LINKER_FLAGS=${LINKER_FLAGS}")
run(${CMAKE_COMMAND} --build ${consumer_build})
run(${consumer_build}/consumer)
# [/snippet:test]
message(STATUS "${last_output}")
