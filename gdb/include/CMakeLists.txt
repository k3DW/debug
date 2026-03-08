# Copyright 2026 Braden Ganetsky
# Distributed under the Boost Software License, Version 1.0.
# https://www.boost.org/LICENSE_1_0.txt

add_library(k3_gdb INTERFACE k3/gdb/framework.hpp)
add_library(k3::gdb ALIAS k3_gdb)
target_include_directories(k3_gdb INTERFACE .)

function(k3_gdb_add_test target)

    add_executable(${target} ${ARGN})
    target_link_libraries(${target} k3::gdb)
    target_compile_options(${target} PRIVATE
        -g
    )

    get_property(this_dir TARGET k3_gdb PROPERTY SOURCE_DIR)
    set(generated_file "${CMAKE_CURRENT_BINARY_DIR}/${target}.k3_gdb.list_of_tests.cmake")
    set(framework_py "${this_dir}/k3/gdb/framework.py")

    add_custom_command(
        TARGET ${target} POST_BUILD
        COMMAND gdb -batch
            -ex "file ${CMAKE_CURRENT_BINARY_DIR}/${target}"
            -ex "python k3_gdb_mode = \"discovery=${generated_file}\""
            -ex "source ${framework_py}"
        COMMAND ${CMAKE_COMMAND}
            -D "TARGET_NAME=${target}"
            -D "BINARY_DIR=${CMAKE_CURRENT_BINARY_DIR}"
            -D "LIST_OF_TESTS_FILE=${generated_file}"
            -D "FRAMEWORK_FILE=${framework_py}"
            -P "${this_dir}/discover_tests_script.cmake"
        COMMAND ${CMAKE_COMMAND}
            -D "BINARY_DIR=${CMAKE_CURRENT_BINARY_DIR}"
            -D "LIST_OF_TESTS_FILE=${generated_file}"
            -P "${this_dir}/include_tests_script.cmake"
        BYPRODUCTS ${generated_file}
        VERBATIM
    )

endfunction()
