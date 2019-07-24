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

"""Implement a trivial text-based file archive format.

The goals for the format are:

    - be trivial enough to create and edit by hand.
    - be able to store trees of text files describing ic command test
      cases.
    - diff nicely in git history and code reviews.

Non-goals include being a completely general archive format, storing
binary data, storing file modes, storing special files like symbolic
links, and so on.

Txtar format

A txtar archive is zero or more comment lines and then a sequence of
file entries.
Each file entry begins with a file marker line of the form
"-- FILENAME --" and is followed by zero or more file content lines
making up the file data.
The comment or file content ends at the next file marker line.
The file marker line must begin with the three-byte sequence "-- " and
end with the three-byte sequence " --", but the enclosed file name can
be surrounding by additional white space, all of which is stripped.

If the txtar file is missing a trailing newline on the final line,
parsers should consider a final newline to be present anyway.

There are no possible syntax errors in a txtar archive.

"""

import pathlib
from typing import Iterable, NamedTuple, Optional, Tuple

MARKER_START = "-- "
MARKER_NEWLINE = "\n" + MARKER_START
MARKER_END = " --"


class File(NamedTuple):

    """A single file in an archive."""

    name: str
    data: str


class Archive(NamedTuple):

    """A collection of files."""

    comment: str
    files: Iterable[File]


def encode(arc: Archive) -> str:
    """Return the serialized form of an Archive.

    It is assumed that the Archive data structure is well-formed, i.e.
    archive comment and all archive file data contain no file marker
    lines, and all archive file names are non-empty.

    """
    return _fix_nl(arc.comment) + "".join(
        map(
            lambda f: f"{MARKER_START}{f.name}{MARKER_END}\n{_fix_nl(f.data)}",
            arc.files,
        )
    )


def parse(data: str) -> Archive:
    """Parse the serialized form of an Archive."""
    comment, name, after = _find_file_marker(data)
    files = []
    while name and after is not None:
        fname = name
        data, name, after = _find_file_marker(after)
        files.append(File(fname, data))
    return Archive(comment, files)


def parse_file(file: pathlib.Path) -> Archive:
    """Parse the named file as an archive."""
    return parse(file.read_text())  # pragma: no cover


def _find_file_marker(data: str) -> Tuple[str, str, Optional[str]]:
    """Find the next file marker in data, extract the file name, and
    return the data before the marker, the file name, and the data
    after the marker.

    If there is no next marker, return before = _fix_nl(data),
    name = "", after = None.

    """
    i = 0
    while True:
        name, after = _is_marker(data[i:])
        if name:
            return data[:i], name, after
        if MARKER_NEWLINE not in data[i:]:
            return _fix_nl(data), "", None
        # positioned at start of new possible marker
        i += data[i:].index(MARKER_NEWLINE) + 1


def _is_marker(data: str) -> Tuple[str, Optional[str]]:
    """Check whether data begins with a file marker line.

    If so, return the name from the line and the data after the line.
    Otherwise return name == "" with an unspecified after.

    """
    after = None
    if not data.startswith(MARKER_START):
        return "", None
    data, _, after = data.partition("\n")
    if not data.endswith(MARKER_END):
        return "", None
    return data[len(MARKER_START) : -len(MARKER_END)].strip(), after


def _fix_nl(data: str) -> str:
    """If data is empty or ends in \\n, return data.
    Otherwise return data with a final \\n added.

    """
    return data if not data or data.endswith("\n") else data + "\n"
