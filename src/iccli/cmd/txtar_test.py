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

import pytest

from .txtar import Archive, File, encode, parse

TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [
        (
            "basic",
            """comment1
comment2
-- file1 --
File 1 text.
-- foo ---
More file 1 text.
-- file 2 --
File 2 text.
-- empty --
-- noNL --
hello world""",
            Archive(
                "comment1\ncomment2\n",
                [
                    File("file1", "File 1 text.\n-- foo ---\nMore file 1 text.\n"),
                    File("file 2", "File 2 text.\n"),
                    File("empty", ""),
                    File("noNL", "hello world\n"),
                ],
            ),
        )
    ],
)


@pytest.mark.parametrize("text,expected", TESTS)
def test(text, expected):
    arc = parse(text)
    assert arc == expected, f"\nhave:\n{_shorten(arc)}\nwant:\n{_shorten(expected)}"
    arc = parse(encode(arc))
    assert arc == expected, f"\nhave:\n{_shorten(arc)}\nwant:\n{_shorten(expected)}"


def _shorten(arc: Archive):  # pragma: no cover
    return f"comment: {arc.comment}\n" + "\n".join(
        map(lambda f: f"file {f.name}: {f.data}", arc.files)
    )
