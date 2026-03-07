# Copyright 2026 Braden Ganetsky
# Distributed under the Boost Software License, Version 1.0.
# https://www.boost.org/LICENSE_1_0.txt

add_library(k3_gdb INTERFACE k3/gdb/framework.hpp)
add_library(k3::gdb ALIAS k3_gdb)
target_include_directories(k3_gdb INTERFACE .)

function(k3_gdb_add_test TARGET_NAME)
    add_executable(${TARGET_NAME} ${ARGN})
    target_link_libraries(${TARGET_NAME} k3::gdb)
    target_compile_options(${TARGET_NAME} PRIVATE
        -g
    )
    add_test(
        NAME "gdb_${TARGET_NAME}"
        COMMAND gdb -batch
            -ex "file ${CMAKE_CURRENT_BINARY_DIR}/${TARGET_NAME}"
            -ex "source ${CMAKE_CURRENT_LIST_DIR}/include/k3/gdb/framework.py"
    )
endfunction()
