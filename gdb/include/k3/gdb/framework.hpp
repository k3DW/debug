// Copyright 2026 Braden Ganetsky
// Distributed under the Boost Software License, Version 1.0.
// https://www.boost.org/LICENSE_1_0.txt

#ifndef K3_GDB_FRAMEWORK_HPP
#define K3_GDB_FRAMEWORK_HPP

#include <vector>

#if defined(__clang__)
#define K3_GDB_NO_INLINE __attribute__((noinline, optnone))
#elif defined(__GNUC__)
#define K3_GDB_NO_INLINE __attribute__((noinline, optimize("O0"), noclone))
#else
#error "Unsupported compiler"
#endif

namespace k3 {
namespace gdb {

template <class... Ts>
K3_GDB_NO_INLINE void _breakpoint_do_not_call_this_directly(const Ts&...) {}

// template <class T = void>
K3_GDB_NO_INLINE void test_start(const char* name) {
    _breakpoint_do_not_call_this_directly(name);
}

// template <class T = void>
K3_GDB_NO_INLINE void test_finish(const char* name) {
    _breakpoint_do_not_call_this_directly(name);
}

template <class T>
K3_GDB_NO_INLINE void assert_prints(const T& actual, const char* expected) {
    _breakpoint_do_not_call_this_directly(actual, expected);
}

template <class T>
K3_GDB_NO_INLINE void expect_prints(const T& actual, const char* expected) {
    _breakpoint_do_not_call_this_directly(actual, expected);
}

using size_t = decltype(sizeof(0));

// Use UDL to guarantee usage of a string literal
constexpr size_t operator ""_k3_gdb_hash(const char* s, size_t size) noexcept {
    size_t hash = 0;
    for (size_t i = 0; i != size; ++i) {
        // rotl by 1, then add the new char
        hash = ((hash << 1) | (hash >> 63)) + static_cast<size_t>(s[i]);
    }
    return hash;
}

class test {
public:
    test(const char* name, void(*func)())
        : _name(name), _func(func)
    {}
    void run() const {
        _run_guard guard{_name};
        _func();
    }
private:
    const char* _name;
    void(*_func)();
    class [[nodiscard]] _run_guard {
        const char* _name;
    public:
        _run_guard(const char* name) {
            _name = name;
            test_start(_name);
        }
        ~_run_guard() {
            test_finish(_name);
        }
    };
};

class runner {
public:
    static runner& get() {
        static runner r;
        return r;
    }
    void exec(int argc, const char* const argv[]) {
        for (const auto& t : _tests) {
            t.run();
        }
    }
    bool add(test t) {
        _tests.push_back(std::move(t));
        return true;
    }
private:
    runner() = default;
    std::vector<test> _tests;
};

inline void main(const int argc, const char* const* const argv) {
    runner::get().exec(argc, argv);
}

} // namespace gdb
} // namespace k3

#define K3_GDB_CAT_(A, B) A ## B
#define K3_GDB_CAT(A, B) K3_GDB_CAT_(A, B)

#define TEST(NAME)                                                                 \
    template <::k3::gdb::size_t hash>                                              \
    class k3_gdb_test_impl_;                                                       \
    template <>                                                                    \
    class k3_gdb_test_impl_<(K3_GDB_CAT(NAME, _k3_gdb_hash))> {                    \
    private:                                                                       \
        static void _k3_gdb_run();                                                 \
        static const bool _k3_gdb_init;                                            \
    };                                                                             \
    const bool k3_gdb_test_impl_<(K3_GDB_CAT(NAME, _k3_gdb_hash))>::_k3_gdb_init = \
        ::k3::gdb::runner::get().add(::k3::gdb::test((NAME), &_k3_gdb_run));       \
    void k3_gdb_test_impl_<(K3_GDB_CAT(NAME, _k3_gdb_hash))>::_k3_gdb_run()

namespace k3 {
namespace gdb {
namespace checks {

using k3::gdb::assert_prints;
using k3::gdb::expect_prints;

} // namespace checks
} // namespace gdb
} // namespace k3

using k3::gdb::operator ""_k3_gdb_hash;

#endif // K3_GDB_FRAMEWORK_HPP
