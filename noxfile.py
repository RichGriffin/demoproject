# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import nox


#
# Utility Functions
#

def _collect_dirs(
    start_dir,
    suffix="_test.py",
    recurse_further=False,
):
    """Recursively collects a list of dirs that contain a file matching the given suffix.
    This works by listing the contents of directories and finding
    directories that have `*_test.py` files.
    """
    # Collect all the directories that have tests in them.
    for parent, subdirs, files in os.walk(start_dir):
        if "./." in parent:
            continue  # Skip top-level dotfiles
        elif any(f for f in files if f.endswith(suffix)):
            # Don't recurse further for tests, since py.test will do that.
            if not recurse_further:
                del subdirs[:]
            # This dir has desired files in it. yield it.
            yield parent
        else:
            # Filter out dirs we don't want to recurse into
            subdirs[:] = [
                s for s in subdirs if s[0].isalpha()
            ]


#
# Tests
#


FOLDERS = sorted(list(_collect_dirs(".")))


def _session_tests(session, folder):
    """Runs py.test for a particular directory."""
    session.chdir(folder)

    if os.path.exists("requirements.txt"):
        session.install("-r", "requirements.txt")

    session.run(
        "pytest",
        *(session.posargs),
        # Pytest will return 5 when no tests are collected. This can happen
        # on travis where slow and flaky tests are excluded.
        # See http://doc.pytest.org/en/latest/_modules/_pytest/main.html
        success_codes=[0, 5]
    )


@nox.session(python=["3.6", "3.7", "3.8"])
@nox.parametrize("folder", FOLDERS)
def py(session, folder):
    """Runs py.test for a folder using the specified version of Python."""
    session.install("-r", "test-requirements.txt")
    _session_tests(session, folder)


#
# Style
#


# Ignore I202 "Additional newline in a section of imports." to accommodate
# region tags in import blocks. Since we specify an explicit ignore, we also
# have to explicitly ignore the list of default ignores:
# `E121,E123,E126,E226,E24,E704,W503,W504` as shown by `flake8 --help`.
def _determine_local_import_names(start_dir):
    """Determines all import names that should be considered "local".
    This is used when running the linter to insure that import order is
    properly checked.
    """
    file_ext_pairs = [os.path.splitext(path) for path in os.listdir(start_dir)]
    return [
        basename
        for basename, extension in file_ext_pairs
        if extension == ".py"
        or os.path.isdir(os.path.join(start_dir, basename))
        and basename not in ("__pycache__")
    ]


FLAKE8_COMMON_ARGS = [
    "--show-source",
    "--builtin=gettext",
    "--max-complexity=20",
    "--import-order-style=google",
    "--exclude=.nox,.cache,env,lib,generated_pb2,*_pb2.py,*_pb2_grpc.py",
    "--ignore=E121,E123,E126,E203,E226,E24,E266,E501,E704,W503,W504,I100,I201,I202",
    "--max-line-length=88",
]


@nox.session
def lint(session):
    session.install("flake8", "flake8-import-order")

    local_names = _determine_local_import_names(".")
    args = FLAKE8_COMMON_ARGS + [
        "--application-import-names",
        ",".join(local_names),
        ".",
    ]
    session.run("flake8", *args)
