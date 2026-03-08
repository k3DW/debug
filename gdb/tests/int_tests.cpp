// Copyright 2026 Braden Ganetsky
// Distributed under the Boost Software License, Version 1.0.
// https://www.boost.org/LICENSE_1_0.txt

#include <k3/gdb/framework.hpp>

int main(int argc, const char** argv) {
    k3::gdb::main(argc, argv);
}

using namespace k3::gdb::checks;

TEST("const lvalue") {
    const int value = 5;
    expect_prints(value, "5");
}

TEST("lvalue") {
    int value = 6;
    expect_prints(value, "6");
}

TEST("xvalue") {
    int value = 7;
    expect_prints(std::move(value), "7");
}

TEST("prvalue") {
    expect_prints(8, "8");
}
