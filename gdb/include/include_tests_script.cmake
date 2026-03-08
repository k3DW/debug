# Copyright 2024-2026 Braden Ganetsky
# Distributed under the Boost Software License, Version 1.0.
# https://www.boost.org/LICENSE_1_0.txt

# Expected variables:
#   BINARY_DIR
#   LIST_OF_TESTS_FILE

set(CTEST_FILE "${BINARY_DIR}/CTestTestfile.cmake")

file(LOCK "${CTEST_FILE}.lock" GUARD PROCESS TIMEOUT 15)

file(READ "${CTEST_FILE}" ctest_file_contents)
string(FIND "${ctest_file_contents}" "${LIST_OF_TESTS_FILE}" found_position)
if(found_position EQUAL -1)
    file(APPEND "${CTEST_FILE}" "include(${LIST_OF_TESTS_FILE})\n")
endif()

file(LOCK "${CTEST_FILE}.lock" RELEASE)
