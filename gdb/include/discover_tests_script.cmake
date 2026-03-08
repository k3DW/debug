# Copyright 2024-2026 Braden Ganetsky
# Distributed under the Boost Software License, Version 1.0.
# https://www.boost.org/LICENSE_1_0.txt

# Expected variables:
#   TARGET_NAME
#   BINARY_DIR
#   LIST_OF_TESTS_FILE
#   FRAMEWORK_FILE

file(READ "${LIST_OF_TESTS_FILE}" list_of_tests_contents)
string(REGEX REPLACE
    "(\"([^\n]+)\")\n"
    "
        add_test(
            [===[\\1]===]
            gdb -batch
                -ex [===[file ${BINARY_DIR}/${TARGET_NAME}${CMAKE_EXECUTABLE_SUFFIX}]===]
                -ex [===[python k3_gdb_mode = \"run=\\2\"]===]
                -ex [===[source ${FRAMEWORK_FILE}]===]
        )
    "
    list_of_tests_contents "${list_of_tests_contents}"
)
file(WRITE "${LIST_OF_TESTS_FILE}" "${list_of_tests_contents}")
