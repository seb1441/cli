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

import logging
from functools import lru_cache
from typing import Iterable, Mapping

import pytest

from . import brick
from .mvs import build_list, downgrade, req, upgrade, upgrade_all

LOGGER = logging.getLogger(__name__)

TESTS = """
# Scenario from blog.
name: blog
A: B1 C2
B1: D3
C1: D2
C2: D4
C3: D5
C4: G1
D2: E1
D3: E2
D4: E2 F1
D5: E2
G1: C4
A2: B1 C4 D4
build A: A B1 C2 D4 E2 F1
upgrade* A: A B1 C4 D5 E2 G1
upgrade A C4: A B1 C4 D4 E2 F1 G1
downgrade A2 D2: A2 C4 D2

name: trim
A: B1 C2
B1: D3
C2: B2
B2:
build A: A B2 C2

# Cross-dependency between D and E.
# No matter how it arises, should get result of merging all build lists via max,
# which leads to including both D2 and E2.

name: cross1
A: B C
B: D1
C: D2
D1: E2
D2: E1
build A: A B C D2 E2

name: cross1V
A: B2 C D2 E1
B1: 
B2: D1
C: D2
D1: E2
D2: E1
build A: A B2 C D2 E2

name: cross1U
A: B1 C
B1: 
B2: D1
C: D2
D1: E2
D2: E1
build A: A B1 C D2 E1
upgrade A B2: A B2 C D2 E2

name: cross1R
A: B C 
B: D2
C: D1
D1: E2
D2: E1
build A: A B C D2 E2

name: cross1X
A: B C
B: D1 E2
C: D2
D1: E2
D2: E1
build A: A B C D2 E2

name: cross2
A: B D2
B: D1
D1: E2
D2: E1
build A: A B D2 E2

name: cross2X
A: B D2
B: D1 E2
C: D2
D1: E2
D2: E1
build A: A B D2 E2

name: cross3
A: B D2 E1
B: D1
D1: E2
D2: E1
build A: A B D2 E2

name: cross3X
A: B D2 E1
B: D1 E2
D1: E2
D2: E1
build A: A B D2 E2

# Should not get E2 here, because B has been updated
# not to depend on D1 anymore.
name: cross4
A1: B1 D2
A2: B2 D2
B1: D1
B2: D2
D1: E2
D2: E1
build A1: A1 B1 D2 E2
build A2: A2 B2 D2 E1

# But the upgrade from A1 preserves the E2 dep explicitly.
upgrade A1 B2: A1 B2 D2 E2
upgradereq A1 B2: B2 E2

name: cross5
A: D1
D1: E2
D2: E1
build A: A D1 E2
upgrade* A: A D2 E2
upgrade A D2: A D2 E2
upgradereq A D2: D2 E2

name: cross6
A: D2
D1: E2
D2: E1
build A: A D2 E1
upgrade* A: A D2 E2
upgrade A E2: A D2 E2

name: cross7
A: B C
B: D1
C: E1
D1: E2
E1: D2
build A: A B C D2 E2

# Upgrade from B1 to B2 should drop the transitive dep on D.
name: drop
A: B1 C1
B1: D1
B2:
C2:
D2:
build A: A B1 C1 D1
upgrade* A: A B2 C2

name: simplify
A: B1 C1
B1: C2
C1: D1
C2:
build A: A B1 C2

name: up1
A: B1 C1
B1:
B2:
B3:
B4:
B5.hidden:
C2:
C3:
build A: A B1 C1
upgrade* A: A B4 C3

name: up2
A: B5.hidden C1
B1:
B2:
B3:
B4:
B5.hidden:
C2:
C3:
build A: A B5.hidden C1
upgrade* A: A B5.hidden C3

name: down1
A: B2
B1: C1
B2: C2
build A: A B2 C2
downgrade A C1: A B1

name: down2
A: B2 E2
B1:
B2: C2 F2
C1:
D1:
C2: D2 E2
D2: B2
E2: D2
E1:
F1:
downgrade A F1: A B1 E1

name: down3
A: 

# golang.org/issue/25542.
name: noprev1
A: B4 C2
B2.hidden: 
C2: 
downgrade A B2.hidden: A B2.hidden C2

name: noprev2
A: B4 C2
B2.hidden: 
B1: 
C2: 
downgrade A B2.hidden: A B2.hidden C2

name: noprev3
A: B4 C2
B3: 
B2.hidden: 
C2: 
downgrade A B2.hidden: A B2.hidden C2

# Cycles involving the target.

# The target must be the newest version of itself.
name: cycle1
A: B1
B1: A1
B2: A2
B3: A3
build A: A B1
upgrade A B2: A B2
upgrade* A: A B3

# Requirements of older versions of the target
# must not be carried over.
name: cycle2
A: B1
A1: C1
A2: D1
B1: A1
B2: A2
C1: A2
C2:
D2:
build A: A B1
upgrade* A: A B2

# Requirement minimization.

name: req1
A: B1 C1 D1 E1 F1
B1: C1 E1 F1
req A: B1 D1
req A C: B1 C1 D1

name: req2
A: G1 H1
G1: H1
H1: G1
req A: G1
req A G: G1
req A H: H1

# ---

name: blog2
A: B2 C2
B1: D1
B2: D3
C1:
C2: D4
C3: F1
D1: E1
D2: E1
D3: E2
D4: E2
E1:
E2:
E3:
F1: G1
G1: F1
build A: A B2 C2 D4 E2
upgrade* A: A B2 C3 D4 E3 F1 G1
upgrade A C3: A B2 C3 D4 E2 F1 G1
downgrade A D2: A B1 C1
upgradereq A C3: B2 C3 D4

name: min
A: B1 C2
B1: C1
req A B C: B1 C2
"""


def dotify(spec):  # pragma: no cover
    res = []
    for line in filter(lambda l: l and l[0] != "#", map(str.strip, spec.splitlines())):
        key, vals = map(str.strip, line.split(":"))
        if "." in key:
            key = f'"{key}"'
        if not vals:
            res.append((key,))
        for val in vals.split():
            if "." in val:
                val = f'"{val}"'
            res.append((key, val))
    res = "\n".join(map("->".join, res))
    return f"digraph G {{\n{res}\n}}"


class Reqs:
    def __init__(self, graph: Mapping[brick.Brick, Iterable[brick.Brick]]):
        self.graph = graph

    def required(self, brk: brick.Brick) -> Iterable[brick.Brick]:
        if brk not in self.graph:
            raise ValueError(f"missing brick: {brk!r}")  # pragma: no cover
        return self.graph[brk]

    def max(self, ver1: str, ver2: str) -> str:
        # pylint: disable=no-self-use
        if ver1 == "none" or ver2 == "":
            return ver2
        if ver2 == "none" or ver1 == "":
            return ver1
        return ver2 if ver1 < ver2 else ver1

    def upgrade(self, brk: brick.Brick) -> brick.Brick:
        res = brick.Brick("", "")
        for curr in self.graph.keys():
            if (
                curr.name == brk.name
                and res.version < curr.version
                and not curr.version.endswith(".hidden")
            ):
                res = curr
        if res.name == "":
            raise ValueError(f"missing brick: {brk.name!r}")  # pragma: no cover
        return res

    def previous(self, brk: brick.Brick) -> brick.Brick:
        res = brick.Brick("", "")
        for curr in self.graph.keys():
            if (
                curr.name == brk.name
                and res.version < curr.version
                and curr.version < brk.version
                and not curr.version.endswith(".hidden")
            ):
                res = curr
        if res.name == "":
            return brick.Brick(brk.name, "none")
        return res


@lru_cache(maxsize=None)
def _parse(data):
    res = []
    for line in filter(lambda l: l and l[0] != "#", map(str.strip, data.splitlines())):
        key, val = map(str.strip, line.split(":"))
        fields = key.split()
        if fields[0] == "name":
            name = val
            graph = {}
            continue
        if not fields[0].islower():
            vals = list(map(lambda v: brick.Brick(v[0], v[1:]), val.split()))
            graph[brick.Brick(key[0], key[1:])] = vals
            for req_ in vals:
                graph.setdefault(req_, [])
        else:
            oper = fields[0]
            reqs = Reqs(graph)
            args = list(map(lambda v: brick.Brick(v[0], v[1:]), fields[1:]))
            expected = list(map(lambda v: brick.Brick(v[0], v[1:]), val.split()))
            res.append(("_".join([name, *fields]), oper, reqs, args, expected))
    return res


BUILD_TESTS = map(
    lambda t: pytest.param(*t[2:], id=t[0]),
    filter(lambda t: t[1] == "build", _parse(TESTS)),
)


@pytest.mark.parametrize("reqs,args,expected", BUILD_TESTS)
def test_build_list(reqs, args, expected):
    if len(args) != 1:
        raise TypeError("build takes one argument")  # pragma: no cover
    actual = build_list(args[0], reqs)
    assert len(expected) == len(actual)
    assert all([a == b for a, b in zip(expected, actual)])


UPGRADE_ALL_TESTS = map(
    lambda t: pytest.param(*t[2:], id=t[0]),
    filter(lambda t: t[1] == "upgrade*", _parse(TESTS)),
)


@pytest.mark.parametrize("reqs,args,expected", UPGRADE_ALL_TESTS)
def test_upgrade_all(reqs, args, expected):
    if len(args) != 1:
        raise TypeError("upgrade* takes one argument")  # pragma: no cover
    actual = upgrade_all(args[0], reqs)
    assert len(expected) == len(actual)
    assert all([a == b for a, b in zip(expected, actual)])


UPGRADE_REQ_TESTS = map(
    lambda t: pytest.param(*t[2:], id=t[0]),
    filter(lambda t: t[1] == "upgradereq", _parse(TESTS)),
)


@pytest.mark.parametrize("reqs,args,expected", UPGRADE_REQ_TESTS)
def test_upgrade_req(reqs, args, expected):
    if not args:
        raise TypeError("upgradereq takes at least one argument")  # pragma: no cover
    actual = upgrade(args[0], reqs, *args[1:])
    actual = req(args[0], actual, [], reqs)
    assert len(expected) == len(actual)
    assert all([a == b for a, b in zip(expected, actual)])


UPGRADE_TESTS = map(
    lambda t: pytest.param(*t[2:], id=t[0]),
    filter(lambda t: t[1] == "upgrade", _parse(TESTS)),
)


@pytest.mark.parametrize("reqs,args,expected", UPGRADE_TESTS)
def test_upgrade(reqs, args, expected):
    if not args:
        raise TypeError("upgrade takes at least one argument")  # pragma: no cover
    actual = upgrade(args[0], reqs, *args[1:])
    assert len(expected) == len(actual)
    assert all([a == b for a, b in zip(expected, actual)])


DOWNGRADE_TESTS = map(
    lambda t: pytest.param(*t[2:], id=t[0]),
    filter(lambda t: t[1] == "downgrade", _parse(TESTS)),
)


@pytest.mark.parametrize("reqs,args,expected", DOWNGRADE_TESTS)
def test_downgrade(reqs, args, expected):
    if not args:
        raise TypeError("downgrade takes at least one argument")  # pragma: no cover
    actual = downgrade(args[0], reqs, *args[0:])
    assert len(expected) == len(actual)
    assert all([a == b for a, b in zip(expected, actual)])


REQ_TESTS = map(
    lambda t: pytest.param(*t[2:], id=t[0]),
    filter(lambda t: t[1] == "req", _parse(TESTS)),
)


@pytest.mark.parametrize("reqs,args,expected", REQ_TESTS)
def test_req(reqs, args, expected):
    if not args:
        raise TypeError("req takes at least one argument")  # pragma: no cover
    actual = build_list(args[0], reqs)
    actual = req(args[0], actual, list(map(lambda b: b.name, args[1:])), reqs)
    assert len(expected) == len(actual)
    assert all([a == b for a, b in zip(expected, actual)])
