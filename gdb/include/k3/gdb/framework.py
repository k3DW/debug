# Copyright 2026 Braden Ganetsky
# Distributed under the Boost Software License, Version 1.0.
# https://www.boost.org/LICENSE_1_0.txt

import gdb

import enum
import json
import re
import sys

breakpoint = gdb.Breakpoint("k3::gdb::_breakpoint_do_not_call_this_directly")
breakpoint.commands = "k3_gdb\ncontinue"
breakpoint.silent = True

class Fatality(enum.Enum):
    NON_FATAL = 0
    FATAL = 1

class Error:
    def __init__(self,
                 fatality: Fatality,
                 file: str,
                 line: int,
                 expected: str,
                 actual: str,
                 ):
        self.fatality: Fatality = fatality
        self.file : str = file
        self.line : int = line
        self.expected : str = expected
        self.actual : str = actual

class TestResult:
    def __init__(self, name: str):
        self.name : str = name
        self.num_checks : int = 0
        self.errors : list[Error] = []

class TestRunner:
    def __init__(self):
        self.test_results : dict[str, TestResult] = {}
        self.current_test_results : TestResult | None = None
        self.skip_to_next_test : bool = False

def read_char_ptr(frame: gdb.Frame, identifier: str) -> str:
    value = frame.read_var(identifier)
    assert f"{value.type}" == "const char *"
    match = re.search(r"0x[A-Fa-f0-9]+ (\".*\")$", f"{value}")
    assert match is not None
    return json.loads(match.group(1))



framework_errors : list[str] = []
callbacks_cls : type = None
runner = TestRunner()

class Command(gdb.Command):
    def __init__(self):
        super().__init__("k3_gdb", gdb.COMMAND_DATA)

    def invoke(self, arg, from_tty):
        try:
            breakpoint_frame = gdb.newest_frame()
            frame = breakpoint_frame.older()
            frame.select()

            call_info = frame.older().find_sal()

            if frame.name() == "k3::gdb::test_start":
                callbacks_cls.on_test_start(read_char_ptr(frame, "name"))
            elif frame.name() == "k3::gdb::test_finish":
                callbacks_cls.on_test_finish(read_char_ptr(frame, "name"))
            elif frame.name().startswith("k3::gdb::expect_prints<") or frame.name().startswith("k3::gdb::assert_prints<"):
                callbacks_cls.on_check_prints(frame, call_info)
            else:
                call_site = f"{call_info.symtab.filename}:{call_info.line}"
                framework_errors.append(f"Hit breakpoint in unrecognized stack frame\n\t{frame.name()}\n\t{call_site}")

        except RuntimeError as e:
            # Quoting the libc++ GDB pretty-printer tests:
            #   > At this point, lots of different things could be wrong, so don't try to
            #     recover or figure it out. Don't exit either, because then it's
            #     impossible debug the framework itself.
            framework_errors.append(f"Unknown error: {e}")

def exit_handler(event):
    if len(framework_errors) != 0:
        print(f"Saw {len(framework_errors)} k3::gdb framework errors:")
        for e in framework_errors:
            print(f"    k3::gdb framework error: {e}")
        sys.exit(1)

    callbacks_cls.on_exit_handler() # This function should exit
    sys.exit(0) # We shouldn't reach this, but just in case



class RunCallbacks:
    test_name : str | None = None

    @staticmethod
    def on_test_start(test_name: str):
        if RunCallbacks.test_name is not None and test_name != RunCallbacks.test_name:
            runner.skip_to_next_test = True
        else:
            if test_name in runner.test_results:
                framework_errors.append(f"Test name seen twice: {test_name}")
            runner.test_results[test_name] = TestResult(test_name)
            assert runner.current_test_results is None
            runner.current_test_results = runner.test_results[test_name]

    @staticmethod
    def on_test_finish(test_name: str):
        if RunCallbacks.test_name is not None and test_name != RunCallbacks.test_name:
            runner.skip_to_next_test = False
        else:
            if test_name not in runner.test_results:
                framework_errors.append(f"Test name missing: {test_name}")
            assert runner.current_test_results is not None
            runner.current_test_results = None
            runner.skip_to_next_test = False

    @staticmethod
    def on_check_prints(frame: gdb.Frame, call_info: gdb.Symtab_and_line):
        if runner.skip_to_next_test:
            return
        runner.current_test_results.num_checks += 1

        actual = frame.read_var("actual")
        assert actual.type.code == gdb.TYPE_CODE_REF
        actual_str = f"{actual.referenced_value()}"

        expected_str = read_char_ptr(frame, "expected")

        if actual_str != expected_str:
            fatality = [Fatality.NON_FATAL, Fatality.FATAL][frame.name().startswith("k3::gdb::assert_")]
            runner.current_test_results.errors.append(Error(fatality=fatality,
                                                            file=call_info.symtab.filename,
                                                            line=call_info.line,
                                                            expected=expected_str,
                                                            actual=actual_str))
            if fatality == Fatality.FATAL:
                runner.skip_to_next_test = True

    @staticmethod
    def on_exit_handler():
        all_passed = True

        for test in runner.test_results.values():
            if len(test.errors) == 0:
                print(f"Test {json.dumps(test.name)} passed all {test.num_checks} checks.")
            else:
                all_passed = False
                print(f"Test {json.dumps(test.name)} failed {len(test.errors)} checks of {test.num_checks}.")
                for e in test.errors:
                    fatality = ["Non-fatal", "Fatal"][e.fatality == Fatality.FATAL]
                    print(f"    {fatality} error at {e.file}:{e.line}\n        Expected: {e.expected}\n        Actual:   {e.actual}")
            print()

        if (all_passed):
            sys.exit(0)
        else:
            sys.exit(1)



class DiscoveryCallbacks:
    output_file : str | None = None

    @staticmethod
    def on_test_start(test_name: str):
        if test_name in runner.test_results:
            framework_errors.append(f"Test name seen twice: {test_name}")
        else:
            runner.test_results[test_name] = TestResult(test_name)
        assert runner.current_test_results is None
        runner.current_test_results = runner.test_results[test_name]

    @staticmethod
    def on_test_finish(test_name: str):
        if test_name not in runner.test_results:
            framework_errors.append(f"Test name missing: {test_name}")
        assert runner.current_test_results is not None
        runner.current_test_results = None
        runner.skip_to_next_test = False

    @staticmethod
    def on_check_prints(frame: gdb.Frame, call_info: gdb.Symtab_and_line):
        pass

    @staticmethod
    def on_exit_handler():
        output_file = DiscoveryCallbacks.output_file
        if output_file is None:
            print(f"Discovered {len(runner.test_results)} k3::gdb tests:")
            for test in runner.test_results:
                print(json.dumps(test))
        else:
            with open(output_file, "w") as file:
                for test in runner.test_results:
                    file.write(f"{json.dumps(test)}\n")
            print(f"Discovered {len(runner.test_results)} k3::gdb tests, written to {output_file}")
        sys.exit(0)



if 'k3_gdb_mode' in globals():
    k3_gdb_mode = k3_gdb_mode
    assert type(k3_gdb_mode) == str
    if k3_gdb_mode.startswith("run"):
        match = re.search(r"^run(?:=(.+))?$", k3_gdb_mode)
        if match is None:
            print(f"Unrecognized 'k3_gdb_mode' for 'run': {json.dumps(k3_gdb_mode)}")
            sys.exit(1)
        callbacks_cls = RunCallbacks
        RunCallbacks.test_name = match.group(1)
    elif k3_gdb_mode.startswith("discovery"):
        match = re.search(r"^discovery(?:=(.+))?$", k3_gdb_mode)
        if match is None:
            print(f"Unrecognized 'k3_gdb_mode' for 'discovery': {json.dumps(k3_gdb_mode)}")
            sys.exit(1)
        callbacks_cls = DiscoveryCallbacks
        DiscoveryCallbacks.output_file = match.group(1)
    else:
        print(f"Unrecognized 'k3_gdb_mode': {json.dumps(k3_gdb_mode)}")
        sys.exit(1)
else:
    callbacks_cls = RunCallbacks



# The rest of this file is procedurally identical to the
# libc++ GDB pretty-printer tests, and copies their comments.

# Disable terminal paging
gdb.execute("set height 0")
gdb.execute("set python print-stack full")

Command()

# "run" won't return if the program exits; ensure the script regains control.
gdb.events.exited.connect(exit_handler)
gdb.execute("run")

# If the program didn't exit, something went wrong, but we don't
# know what. Fail on exit.
framework_errors.append("Program did not exit, therefore something went wrong")
exit_handler(None)
