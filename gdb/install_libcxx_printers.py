#!/usr/bin/env python3
# Copyright 2025 Braden Ganetsky
# Distributed under the Boost Software License, Version 1.0.
# https://www.boost.org/LICENSE_1_0.txt

import argparse
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

def find_real_path(path : str) -> str:
    if not os.path.exists(path):
        raise RuntimeError(f"File does not exist: {path}")
    if not os.path.isfile(path) and not os.path.islink(path):
        raise RuntimeError(f"Path is not a real file or a link: {path}")
    return os.path.realpath(path)

def download_file(url : str, file_path : str) -> bool:
    def has_write_access(path) -> bool:
        path = Path(path)
        while (True):
            if path.exists():
                return os.access(path, os.W_OK)
            path = path.parent

    if not has_write_access(file_path):
        return False

    Path(file_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            with open(file_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
        return True
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP Error: {e.code} {e.reason}\n'{url}'") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL Error: {e.reason}\n'{url}'") from e
    except TimeoutError:
        raise RuntimeError(f"Download timed out. The server did not respond within 10 seconds.\n'{url}'") from e
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred: {e}") from e



def find_libcxx_version(libcxx_so_path : str) -> str:
    def run_command(args : list) -> str:
        try:
            return subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=True
            ).stdout
        except FileNotFoundError as e:
            raise RuntimeError(f"Error: command \"{args[0]}\" not found") from e

    def extract_version_numbers(lines : list[str], re_prefix : str, re_suffix : str) -> list[str]:
        version_pattern = r"\d+\.\d+\.\d+"
        pattern = f"{re_prefix}({version_pattern}){re_suffix}"
        versions = set()
        for line in lines:
            match = re.search(pattern, line)
            if match:
                versions.add(match.group(1))
        return list(versions)

    def find_installed_libcxx_package_versions() -> list[str]:
        result = run_command(["dpkg", "-l"])
        lines = [line
            for line in result.splitlines()
            if "  libc++" in line]
        return extract_version_numbers(lines, "1:", "~")

    def find_libcxx_so_version(libcxx_so_path : str) -> str:
        cmake_var = "LLVM_PACKAGE_VERSION"
        libcxx_so_dir = Path(find_real_path(libcxx_so_path)).parent
        result = run_command(["grep", "-r", cmake_var, libcxx_so_dir])
        lines = result.splitlines()
        versions = extract_version_numbers(lines, f"set\({cmake_var} ", "\)")
        if len(versions) == 0:
            raise RuntimeError(f"Unable to find \"{cmake_var}\" in {libcxx_so_dir}")
        elif len(versions) != 1:
            versions = ", ".join(versions)
            raise RuntimeError(f"Found more than one definition of \"{cmake_var}\":\n\t{versions}")
        return versions[0]

    so_version = find_libcxx_so_version(libcxx_so_path)
    package_versions = find_installed_libcxx_package_versions()
    if so_version not in package_versions:
        print(f"Warning: {libcxx_so_path} version found to be {so_version}, does not match installed package versions: {package_versions}")
    return so_version



def auto_load_file_contents(download_to : str, module_name : str) -> str:
    return (
        "# Copyright 2025 Braden Ganetsky\n"
        "# Distributed under the Boost Software License, Version 1.0.\n"
        "# https://www.boost.org/LICENSE_1_0.txt\n"
        "\n"
        "import gdb\n"
        "import sys\n"
        "\n"
        "# Update module path. GCC does this with relative paths for\n"
        "# relocatability, but this script is much simpler\n"
       f"pythondir = \"{download_to}\"\n"
        "if not pythondir in sys.path:\n"
        "    sys.path.insert(0, pythondir)\n"
        "\n"
       f"import {module_name}\n"
       f"{module_name}.register_libcxx_printer_loader()\n"
    )



def parse_args() -> dict:
    def make_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description="Download and install libc++ GDB pretty-printers from 'https://github.com/llvm/llvm-project'."
        )

        group = parser.add_mutually_exclusive_group(required=False)
        group.add_argument(
            "-t", "--tag",
            metavar="TAG_NAME",
            type=str,
            help="Download from the given tag name.",
        )
        group.add_argument(
            "-b", "--branch",
            metavar="BRANCH_NAME",
            type=str,
            help="Download from the given branch name.",
        )
        group.add_argument(
            "-c", "--commit",
            metavar="COMMIT_HASH",
            type=str,
            help="Download from the given commit hash.",
        )

        parser.add_argument(
            "-d", "--download-to",
            metavar="PATH",
            type=str,
            required=False,
            help="Where to download printers.py. Default is '%(default)s'.",
            default="/usr/local/share/gdb/libcxx",
        )

        parser.add_argument(
            "-l", "--libcxx-so",
            metavar="PATH",
            type=str,
            required=False,
            help=(
                "Location of the libc++ shared object. "
                "If no other tag, branch, or commit is specified, "
                "the printers.py file is downloaded based on the version of this shared object. "
                "Default is '%(default)s'."
            ),
            default="/usr/lib/x86_64-linux-gnu/libc++.so.1",
        )

        return parser

    parser = make_parser()
    args = parser.parse_args()
    if args.tag:
        url_middle = f"refs/tags/{args.tag}"
        file_suffix = "tag_" + args.tag
    elif args.branch:
        url_middle = f"refs/heads/{args.branch}"
        file_suffix = "branch_" + args.branch
    elif args.commit:
        url_middle = args.commit
        file_suffix = "commit_" + args.commit[:11]
    else:
        version = find_libcxx_version(args.libcxx_so)
        url_middle = f"refs/tags/llvmorg-{version}"
        file_suffix = f"tag_llvmorg_{version}"

    file_suffix = ''.join([
        (char if char.lower() in "_abcdefghijklmnopqrstuvwxyz0123456789" else "_")
        for char in file_suffix])

    return {
        "url" : f"https://raw.githubusercontent.com/llvm/llvm-project/{url_middle}/libcxx/utils/gdb/libcxx/printers.py",
        "file_name" : f"libcxx_printers_{file_suffix}",
        "download_to" : args.download_to,
        "libcxx_so_path" : find_real_path(args.libcxx_so)
    }



def main():
    args = parse_args()

    url = args["url"]
    file_name = args["file_name"]
    download_to = args["download_to"]
    libcxx_so_path = args["libcxx_so_path"]

    file_path = f"{download_to}/{file_name}.py"
    if not download_file(url, file_path):
        print(f"Permission denied: '{file_path}'")
        sys.exit(1)
    print(f"Successfully downloaded: '{url}'")
    print(f"...and saved file to: '{file_path}'")

    auto_load_file_path = f"/usr/share/gdb/auto-load{libcxx_so_path}-gdb.py"
    with open(auto_load_file_path, "w") as auto_load_file:
        auto_load_file.write(auto_load_file_contents(download_to, file_name))
    print(f"Wrote GDB auto-load script to: '{auto_load_file_path}'")

if __name__ == "__main__":
    main()
