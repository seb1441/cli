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

"""Implement Minimal Version Selection.

The ic command must decide which brick version to use in each build. The
list of bricks and versions for use in a given build is called the
'build list'. For stable development, today's build list must also be
tomorrow's build list. But then developers must also be allowed to
change the build list: to upgrade all bricks, to upgrade one brick, or
to downgrade one brick.

The version selection problem therefore is to define the meaning of, and
to give algorithms implementing, these four operations on build lists:

    1. Construct the current build list.
    2. Upgrade all bricks to their latest versions.
    3. Upgrade one brick to a specific newer version.
    4. Downgrade one brick to a specific older version.

This module implements minimal version selection, a new, simple approach
to the version selection problem.

Minimal version selection assumes that each brick declares its own
dependency requirements: a list of minimum versions of other bricks.
Bricks are assumed to follow the import compatibility rule, i.e.
packages in any newer version should work as well as older ones, so a
dependency requirement gives only a minimum version, never a maximum
version or a list of incompatible later versions.

Then the definitions of the four operations are:

    1. To construct the build list for a given target: start the list
       with the target itself, and then append each requirement's own
       build list. If a brick appears in the list multiple times, keep
       only the newest version.
    2. To upgrade all bricks to their latest versions: construct the
       build list, but read each requirement as if it requested the
       latest brick version.
    3. To upgrade one brick to a specific newer version: construct the
       non-upgraded build list and then append the new brick's build
       list. If a brick appears in the list multiple times, keep only
       the newest version.
    4. To downgrade one brick to a specific older version: rewind the
       required version of each top-level requirement until that
       requirement's build list no longer refers to newer versions of
       the downgraded brick.

See https://research.swtch.com/vgo-mvs.
See https://github.com/golang/go/tree/323212b9e6/src/cmd/go/internal/mvs

"""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import (Callable, Iterable, List, MutableMapping, MutableSet,
                    Optional)

from typing_extensions import Protocol

from . import brick


class Reqs(Protocol):
    """The requirement graph on which Minimal Version Selection (MVS)
    operates.

    The version strings are opaque except for the special version
    `"none"` (see the documentation for `brick.Brick`). In particular,
    MVS does not assume that the version strings are semantic versions;
    instead, the `max` method gives access to the comparison operation.

    """

    # pylint: disable=no-self-use,unused-argument

    def required(self, brk: brick.Brick) -> Iterable[brick.Brick]:
        """Return the brick versions explicitly required by `brk`."""
        ...  # pragma: no cover

    def max(self, ver1: str, ver2: str) -> str:
        """Returns the maximum of `ver1` and `ver2` (return either
        `ver1` or `ver2`).

        For all versions `ver`, `max(ver, "none")` must be `ver`, and
        for the `target` passed as the first argument to MVS functions,
        `max(target, ver)` must be `target`.

        """
        ...  # pragma: no cover

    def upgrade(self, brk: brick.Brick) -> brick.Brick:
        """Returns the upgraded version of `brk`, for use during an
        `upgrade_all` operation.

        If `brk` should be kept as is, returns `brk`.
        More typically, `brk.version` will be the version required by
        some other module in the build.

        """
        ...  # pragma: no cover

    def previous(self, brk: brick.Brick) -> brick.Brick:
        """Returns the version of `brk.name` immediately prior to
        `brk.version`, or `"none"` if no such version is known.


        """
        ...  # pragma: no cover


def build_list(
    target: brick.Brick,
    reqs: Reqs,
    upgrader: Optional[Callable[[brick.Brick], brick.Brick]] = None,
) -> Iterable[brick.Brick]:
    """Return the build list for the target brick.

    The first element is the target itself, with the remainder of the
    list sorted by name.

    """

    @dataclass(unsafe_hash=True)
    class Node:
        brk: brick.Brick = field(hash=True)
        required: Iterable[brick.Brick] = field(default_factory=list, hash=False)

    graph: MutableMapping[brick.Brick, Node] = {}
    mins: MutableMapping[str, str] = {}  # map brick name to minimum required version
    todo, done = deque([target]), set()
    while todo:
        # pylint: disable=broad-except
        curr = todo.popleft()
        done.add(curr)
        node = Node(curr)
        graph[curr] = node
        if (
            curr.name not in mins
            or reqs.max(mins[curr.name], curr.version) != mins[curr.name]
        ):
            mins[curr.name] = curr.version
        node.required = reqs.required(curr)
        todo.extend(r for r in node.required if r not in done)
        if upgrader:
            upg = upgrader(curr)
            if upg not in done:
                todo.append(upg)

    # Construct the list by traversing the graph again, replacing older
    # bricks with required minimum versions.
    todo, res = deque([target]), [target]
    processed = {target.name}
    while todo:
        curr = todo.popleft()
        for req_ in graph[curr].required:
            ver = mins[req_.name]
            if req_.name != target.name:
                assert reqs.max(ver, req_.version) == ver
            if req_.name not in processed:
                res.append(brick.Brick(req_.name, ver))
                todo.append(res[-1])
                processed.add(req_.name)
    return [res[0]] + sorted(res[1:], key=lambda b: b.name)


def req(
    target: brick.Brick, blist: Iterable[brick.Brick], base: Iterable[str], reqs: Reqs
) -> Iterable[brick.Brick]:
    """Return the minimal requirement list for the target brick that
    results in the given build list, with the constraint that all brick
    names listed in base must appear in the returned list.

    """
    # Compute postorder, cache requirements.
    postorder: List[brick.Brick] = []
    cache: MutableMapping[brick.Brick, Iterable[brick.Brick]] = {target: []}

    def walk(brk: brick.Brick):
        if brk in cache:
            return
        required = reqs.required(brk)
        cache[brk] = required
        for req_ in required:
            walk(req_)
        postorder.append(brk)

    for brk in blist:
        walk(brk)

    # Walk bricks in reverse post-order, only adding those not implied
    # already.
    have: MutableMapping[str, str] = {}

    def reverse_walk(brk: brick.Brick):
        if brk.name in have and reqs.max(brk.version, have[brk.name]) == have[brk.name]:
            return
        have[brk.name] = brk.version
        for req_ in cache.get(brk, []):
            reverse_walk(req_)

    # Sanitize the given build list searching for duplicates.
    maxs: MutableMapping[str, str] = {}
    for brk in blist:
        if brk.name in maxs:
            maxs[brk.name] = reqs.max(brk.version, maxs[brk.name])
        else:
            maxs[brk.name] = brk.version

    # First walk the base bricks that must be listed.
    mins: List[brick.Brick] = []
    for name in base:
        brk = brick.Brick(name, maxs.get(name, ""))
        mins.append(brk)
        reverse_walk(brk)
    # Now the reverse postorder to bring in anything else.
    for brk in postorder[::-1]:
        if maxs.get(brk.name, "") != brk.version:
            # older version
            continue
        if have.get(brk.name, "") != brk.version:
            mins.append(brk)
            reverse_walk(brk)
    return sorted(mins, key=lambda b: b.name)


def upgrade_all(target: brick.Brick, reqs: Reqs) -> Iterable[brick.Brick]:
    """Return a build list for the target brick in which every brick is
    upgraded to its latest version.

    """

    def _upgrade(brk: brick.Brick) -> brick.Brick:
        return target if brk.name == target.name else reqs.upgrade(brk)

    return build_list(target, reqs, _upgrade)


class _OverrideReqs:
    def __init__(
        self, target: brick.Brick, required: Iterable[brick.Brick], reqs: Reqs
    ):
        self._target = target
        self._required = required
        self._reqs = reqs

    def __getattr__(self, name):
        return getattr(self._reqs, name)

    def required(self, brk: brick.Brick) -> Iterable[brick.Brick]:
        return self._required if brk == self._target else self._reqs.required(brk)


def upgrade(
    target: brick.Brick, reqs: Reqs, *args: brick.Brick
) -> Iterable[brick.Brick]:
    """Return a build list for the target brick in which the given
    additional bricks are upgraded.

    """
    required = list(reqs.required(target)) + list(args)
    return build_list(target, _OverrideReqs(target, required, reqs))


def downgrade(
    target: brick.Brick, reqs: Reqs, *args: brick.Brick
) -> Iterable[brick.Brick]:
    """Return a build list for the target brick in which the given
    additional bricks are downgraded.

    """
    required = reqs.required(target)
    maxs: MutableMapping[str, str] = {r.name: r.version for r in required}
    for arg in args:
        if arg.name not in maxs or reqs.max(maxs[arg.name], arg.version) != arg.version:
            maxs[arg.name] = arg.version
    added: MutableSet[brick.Brick] = set()
    rdeps: MutableMapping[brick.Brick, List[brick.Brick]] = defaultdict(list)
    excluded: MutableSet[brick.Brick] = set()

    def exclude(brk: brick.Brick):
        if brk in excluded:
            return
        excluded.add(brk)
        for dep in rdeps.get(brk, []):
            exclude(dep)

    def add(brk: brick.Brick):
        if brk in added:
            return
        added.add(brk)
        if brk.name in maxs and reqs.max(brk.version, maxs[brk.name]) != maxs[brk.name]:
            exclude(brk)
            return
        for req_ in reqs.required(brk):
            add(req_)
            if req_ in excluded:
                exclude(brk)
                return
            rdeps[req_].append(brk)

    out: List[brick.Brick] = [target]
    for curr in required:
        add(curr)
        while curr in excluded:
            prev = reqs.previous(curr)
            ver = maxs.get(curr.name, "")
            if (
                reqs.max(ver, curr.version) != ver
                and reqs.max(prev.version, ver) != prev.version
            ):
                prev = brick.Brick(prev.name, ver)
            if prev.version == "none":
                break
            add(prev)
            curr = prev
        else:
            out.append(curr)
    return out
