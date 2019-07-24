# Copyright 2019 Farzad Senart and Lionel Suss. All rights reserved.
#
# This file is part of IC CLI.
#
# IC CLI is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# IC CLI is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with IC CLI. If not, see <https://www.gnu.org/licenses/>.
#
# This file incorporates work covered by the following copyright and
# permission notice:
#
#   Copyright (c) 2009 The Go Authors. All rights reserved.
#
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are
#   met:
#
#      * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#      * Redistributions in binary form must reproduce the above
#   copyright notice, this list of conditions and the following disclaimer
#   in the documentation and/or other materials provided with the
#   distribution.
#      * Neither the name of Google Inc. nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#   A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#   OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#   SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#   LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#   THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#   OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import importlib.resources
import logging
import os
import pathlib
import re
import shutil
import subprocess
import uuid
from collections import deque
from typing import Deque, List, MutableMapping

import pytest

from . import txtar
from .testdata import script as script_fixture

LOGGER = logging.getLogger(__name__)

TESTS = map(
    lambda i: pytest.param(
        importlib.resources.read_text(script_fixture, i), id=re.sub(r".txt$", "", i)
    ),
    filter(lambda i: i.endswith(".txt"), importlib.resources.contents(script_fixture)),
)


class _Script:
    cwd: pathlib.Path  # temporary work dir
    cd: pathlib.Path  # current directory; initially cwd
    stdout: str  # standard output from last command
    stderr: str  # standard error from last command
    stdin: str  # standard input for the next command
    env: MutableMapping  # environment mapping (for exec)

    def __init__(self, cwd: pathlib.Path, proxy_url: str):
        self.cwd = cwd
        self.cd = cwd  # pylint: disable=invalid-name
        self.stdout = ""
        self.stderr = ""
        self.stdin = ""
        self.env = dict(
            {
                k: v
                for k, v in os.environ.items()
                if k.startswith(("COV", "PYTEST", "AWS"))
            },
            PWD=str(self.cd),
            ICHOME=str(self.cwd / ".ic"),
            ICPROXY=proxy_url,
            ICAUTH="dummy",
            UUID=str(uuid.uuid4()),
        )

    def cmd_cd(self, neg: bool, args: List[str]):
        """Change to a different directory."""
        if neg:
            raise TypeError("unsupported: ! env")
        if len(args) != 1:
            raise TypeError("usage: cd dir")
        path = pathlib.Path(args[0])
        if not path.is_absolute():
            path = self.cd.joinpath(path)
        path = path.resolve()
        if not path.exists():
            assert False, f"directory {str(path)!r} does not exist"
        if not path.is_dir():
            assert False, f"{str(path)!r} is not a directory"
        self.cd = path
        self.env["PWD"] = str(path)
        LOGGER.info(str(path))

    def cmd_diff(self, neg: bool, args: List[str]):
        """Compare files line by line."""
        self.cmd_exec(neg, ["diff"] + args)

    def cmd_exec(self, neg: bool, args: List[str]):
        """Run the given command."""
        if not args:
            raise TypeError("usage: exec program [args...]")
        res = subprocess.run(
            " ".join(args),
            input=bytes(self.stdin, "utf-8").decode("unicode_escape"),
            cwd=self.cd,
            env=self.env,
            capture_output=True,
            shell=True,
            encoding="utf-8",
        )
        status = res.returncode
        self.stdin = ""
        self.stdout = res.stdout
        self.stderr = res.stderr
        if self.stdout:
            LOGGER.info("[stdout]\n%s", self.stdout)
        if self.stderr:
            LOGGER.info("[stderr]\n%s", self.stderr)
        if not status and neg:
            assert False, "unexpected command success"
        if status and not neg:
            assert False, "unexpected command failure"

    def cmd_exists(self, neg: bool, args: List[str]):
        """Check that the list of files exist."""
        if not args:
            raise TypeError("usage: exists file...")
        for file in args:
            exists = self.cd.joinpath(file).exists()
            if neg and exists:
                assert False, f"{file!r} unexpectedly exists"
            if not neg and not exists:
                assert False, f"{file!r} does not exists"

    def cmd_env(self, neg: bool, args: List[str]):
        """Display or add to the environment."""
        if neg:
            raise TypeError("unsupported: ! env")
        if not args:
            for item in self.env.items():
                LOGGER.info("=".join(item))
            return
        for arg in args:
            if "=" not in arg:
                # display value instead of setting it.
                LOGGER.info("%s=%s", arg, self.env.get(arg))
                continue
            key, val = arg.split("=")
            self.env[key] = val

    def cmd_grep(self, neg: bool, args: List[str]):
        """Check that file content matches a regexp."""
        self._match(neg, args, "", "grep")

    def cmd_ic(self, neg: bool, args: List[str]):
        """Run the ic command."""
        self.cmd_exec(neg, ["ic"] + args)

    def cmd_stderr(self, neg: bool, args: List[str]):
        """Check the last command stderr matches a regexp."""
        self._match(neg, args, self.stderr, "stderr")

    def cmd_stdin(self, neg: bool, args: List[str]):
        """Feed the standard input for the next command"""
        if neg:
            raise TypeError("unsupported: ! stdin")
        if len(args) > 1:
            raise TypeError("usage: stdin 'text'")
        self.stdin = args[0]

    def cmd_stdout(self, neg: bool, args: List[str]):
        """Check the last command stdout matches a regexp."""
        self._match(neg, args, self.stdout, "stdout")

    def _match(self, neg: bool, args: List[str], text: str, name: str):
        count = 0
        if len(args) >= 1 and args[0].startswith("-count="):
            if neg:
                raise TypeError("cannot use -count= with negated match")
            try:
                count = int(args[0][len("-count=") :])
            except ValueError:
                raise TypeError("bad -count=")
            if count < 1:
                raise TypeError("bad -count=: must be at least 1")
            args = args[1:]
        is_grep = name == "grep"
        extra, want = ("", 1) if not is_grep else (" file", 2)
        if len(args) != want:
            raise TypeError(f"usage: {name} [-count=N] 'pattern'{extra}")
        pattern = args[0]
        regex = re.compile(pattern, re.MULTILINE)
        if is_grep:
            name = args[1]  # for error messages
            text = self.cd.joinpath(args[1]).read_text()
        if neg:
            if regex.search(text):
                if is_grep:
                    LOGGER.info("[%s]\n%s\n", name, text)
                assert False, (
                    f"unexpected match for {pattern!r} found in {name!r}: "
                    f"{regex.findall(text)}"
                )
        else:
            if not regex.search(text):
                if is_grep:
                    LOGGER.info("[%s]\n%s\n", name, text)
                assert False, f"no match for {pattern!r} found in {name!r}"
            if count > 0:
                actual = len(regex.findall(text))
                if actual != count:
                    if is_grep:
                        LOGGER.info("[%s]\n%s\n", name, text)
                    assert False, f"have {actual} matches for {pattern!r}, want {count}"


@pytest.mark.parametrize("data", TESTS)
def test_script(data, tmpdir, proxy):
    cwd = pathlib.Path(tmpdir)
    arch = txtar.parse(data)
    for file in arch.files:
        path = cwd.joinpath(file.name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(file.data)
    data = arch.comment
    scr = _Script(cwd, proxy.url())
    while data:
        line, _, data = data.partition("\n")
        if line.startswith("#"):
            LOGGER.info(line)
            continue
        args = _parse(line)
        if not args:
            continue
        LOGGER.info("> %s", line)
        # Command prefix ! means negate the expectations about this
        # command, i.e. command should fail, match should not be found,
        # etc.
        neg = False
        if args[0] == "!":
            neg = True
            args.popleft()
            if not args:
                raise TypeError("! on line by itself")
        # run command
        cmd = getattr(scr, f"cmd_{args[0]}", None)
        if not cmd:
            raise TypeError(f"unknown command {args[0]!r}")
        cmd(neg, list(args)[1:])
    shutil.rmtree(tmpdir)


def _parse(line: str):
    """Parse a single line as a list of space-separated arguments
    subject to environment variable expansion (but not resplitting).

    Single quotes around text disable splitting and expansion.
    To embed a single quote, double it.

    TODO: expansion if needed

    """
    args: Deque = deque()
    arg = ""  # text of current arg so far (need to add line[start:i])
    start = -1  # if >= 0, position where current arg text chunk starts
    quoted = False  # currently processing quoted text
    i = -1
    while True:
        i += 1
        if not quoted and (i >= len(line) or line[i] in {" ", "\t", "\r", "#"}):
            # Found arg-separating space.
            if start >= 0:
                arg += line[start:i]
                args.append(arg)
                start = -1
                arg = ""
            if i >= len(line) or line[i] == "#":
                break
            continue
        if i >= len(line):
            raise TypeError("unterminated quoted argument")
        if line[i] == "'":
            if not quoted:
                # starting a quoted chunk
                if start >= 0:
                    arg += line[start:i]
                start = i + 1
                quoted = True
                continue
            # 'foo''bar' means foo'bar, like in rc shell and Pascal.
            if i + 1 < len(line) and line[i + 1] == "'":
                arg += line[start:i]
                start = i + 1
                i += 1  # skip over second ' before next iteration
                continue
            # ending a quoted chunk
            arg += line[start:i]
            start = i + 1
            quoted = False
            continue
        # found character worth saving; make sure we're saving
        if start < 0:
            start = i
    return args
