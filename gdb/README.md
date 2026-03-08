# k3::gdb

A lightweight unit testing framework for GDB pretty-printers.

## Support

GCC and Clang, C++11 and up.

**Note: You must build with debug symbols (`-g`) when using this library.**

## Usage

At its simplest, you can just copy the contents of `include/` to somewhere of your choosing. This library is entirely self-contained.

### C++ test file

Here is a simple example of a test file. At its core, the C++ portion of this library is just a means to store symbols. Most of the functions do no work, and would be otherwise optimized away.

```cpp
#include <k3/gdb/framework.hpp>

TEST("test 1") {
    using namespace k3::gdb::checks;
    assert_prints(1, "2");
    expect_prints(3, "3");
}
TEST("test 2") {
    k3::gdb::assert_prints(8, "8");
    k3::gdb::expect_prints(9, "9");
}

int main(int argc, const char** argv) {
    k3::gdb::main(argc, argv);
}
```

* The `TEST` macro only accepts a string literal,
* You can choose to fully qualify calls to `k3::gdb::assert_prints` and `k3::gdb::expect_prints`. Alternatively, you can bring in those symbols from `namespace k3::gdb::checks`. This example shows both.
* The right-hand side of a check function must be a `const char*`.

For now, the complete list of checks available is as follows.

* `assert_prints`
* `expect_prints`

If an `expect` check fails, the rest of the test continues. If an `assert` check fails, nothing else is checked for the remainder of the test.

### Manually building and running

Simply building and running the binary itself is not sufficient. Since we are testing GDB output, we need to invoke GDB.

```bash
g++-or-clang++ -g my_test.cpp -I ./include
gdb -batch -ex "file a.out" -ex "source ./include/k3/gdb/framework.py"
```

After some GDB printout, the results of the test are displayed in the console.

```none
Test "test 1" failed 1 check of 1.
    Fatal error at my_test.cpp:5
        Expected: 2
        Actual:   1

Test "test 2" passed all 2 checks.
```

Note that only 1 check was performed in "test 1".

### CMake and CTest

This library is easiest to use with CMake. No need to manually invoke GDB.

```cmake
add_subdirectory(${path_to_where_you_copied_the_include_dir})
k3_gdb_add_test(my_test
    my_test.cpp
)
```

`k3_gdb_add_test` is a convenience function which does the following.

* Create a target with the given name
* Add `-g` as a compiler option
* Link against the `INTERFACE` target `k3_gdb` (alias `k3::gdb`)
* Discover all the tests
* Register the tests with CTest

```bash
cmake -G Ninja -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

Here is the test output from `ctest`.

```none
Test project /path/to/project
    Start 1: "test 1"
1/2 Test #1: "test 1" .........................***Failed    0.31 sec
Breakpoint 1 at 0x1438: k3::gdb::_breakpoint_do_not_call_this_directly. (2 locations)
[Thread debugging using libthread_db enabled]
Using host libthread_db library "/lib/x86_64-linux-gnu/libthread_db.so.1".
[Inferior 1 (process 197667) exited normally]
Test "test 1" failed 1 check of 1.
    Fatal error at /path/to/my_test.cpp:5
        Expected: 2
        Actual:   1


    Start 2: "test 2"
2/2 Test #2: "test 2" .........................   Passed    0.28 sec

50% tests passed, 1 tests failed out of 2

Total Test time (real) =   0.62 sec

The following tests FAILED:
          1 - "test 1" (Failed)
Errors while running CTest
```

## Future work

Work on this library is ongoing. Most notably, we are currently missing a mechanism to specify GDB pretty-printer scripts to the CMake function.
