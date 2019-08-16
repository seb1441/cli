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

import ast
import json
import logging
import os
import pathlib
import re
import shutil
import zipfile
from collections import OrderedDict, deque
from functools import lru_cache
from itertools import chain
from typing import (
    Any,
    BinaryIO,
    Iterable,
    List,
    MutableMapping,
    MutableSet,
    Optional,
    Sequence,
    Set,
    TextIO,
    Tuple,
    cast,
)

import requests
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import PreservedScalarString

from . import brick, config, mvs, util

LOGGER = logging.getLogger(__name__)


def init(cwd: pathlib.Path):
    """Locate the root of the current brick (if any), load the
    brick.yaml manifest and init globals.

    """
    root = find(cwd)
    man = brick.parse(root)
    brick.MANIFEST.set(man)
    brick.TARGET.set(brick.Brick(man.name, ""))
    brick.ROOT.set(root)
    brick.BUILD_LIST.set([brick.TARGET.get()] + list(man.require))


def find(cwd: pathlib.Path) -> pathlib.Path:
    """Return the path of the directory containing the brick.yaml file.

    Try to find a brick.yaml file in the given directory. If not found
    try with the parent directory and so on.

    """
    while True:
        if cwd.joinpath("brick.yaml").exists():
            return cwd
        if cwd == cwd.parent:
            raise FileNotFoundError
        cwd = cwd.parent


def save(used: Set[str]):
    """Update the current brick.yaml file."""

    # drop unused bricks
    asked = {b.name for b in brick.MANIFEST.get().require}
    keep: List[brick.Brick] = [brick.TARGET.get()]
    for brk in brick.BUILD_LIST.get([]):
        if brk.name in used:
            keep.append(brk)
        elif brk.name in asked:
            LOGGER.info("unused %s %s", brk.name, brk.version)
    brick.BUILD_LIST.set(keep)
    dirs = [d.name for d in directs()]
    mins = mvs.req(brick.TARGET.get(), brick.BUILD_LIST.get(), dirs, Reqs())
    brick.MANIFEST.get().require = mins

    # format and save
    yaml = YAML()
    man = brick.MANIFEST.get()
    file = brick.ROOT.get().joinpath("brick.yaml")
    data: Any = {}
    if file.exists():
        data = yaml.load(file.read_text())
    order: MutableMapping[str, Any] = OrderedDict()
    order["name"] = man.name
    order["version"] = man.version
    order["license"] = man.license or None
    order["private"] = man.private or None
    desc = man.description
    if len(desc) <= 59:
        order["description"] = desc or None
    else:
        order["description"] = PreservedScalarString("\n".join([desc[:70], desc[70:]]))
    order["main"] = man.main
    reqs = sorted(man.require, key=lambda r: r.name)
    order["require"] = dict(OrderedDict((r.name, r.version) for r in reqs)) or None
    repls: MutableMapping[str, Any] = OrderedDict()
    for repl in sorted(man.replace.items(), key=lambda r: r[0]):
        if isinstance(repl[1], pathlib.Path):
            repls[repl[0]] = str(repl[1])
        else:
            repls[repl[0]] = " ".join([repl[1].name, repl[1].version])
    order["replace"] = dict(repls) or None
    excs = sorted(man.exclude, key=lambda r: r.name)
    order["exclude"] = dict(OrderedDict((r.name, r.version) for r in excs)) or None
    order.update({k: v for k, v in data.items() if k not in set(order.keys())})
    with file.open("w") as handle:
        yaml.dump({k: v for k, v in order.items() if v is not None}, handle)


def load() -> Iterable[brick.Brick]:
    """Return bricks used by target and its dependencies, download and
    install missing requirements.

    """
    reqs = Reqs()
    brick.BUILD_LIST.set(list(mvs.build_list(brick.TARGET.get(), reqs)))
    while True:
        used: MutableSet[brick.Brick] = set()
        todo = deque([brick.TARGET.get().name])
        stable = True
        while todo:
            name = todo.popleft()
            brk, path = resolve(name)
            if path:
                if brk not in used:
                    used.add(brk)
                    todo.extend(imports(path))
                continue
            brick.BUILD_LIST.get().append(brk)
            stable = False
        if stable:
            break
        brick.BUILD_LIST.set(list(mvs.build_list(brick.TARGET.get(), reqs)))

    # A given brick path may be used as itself or as a replacement for
    # another brick, but not both at the same time.
    fst: MutableMapping[str, str] = {}
    for brk in brick.BUILD_LIST.get([]):
        src = brk
        alias = brick.MANIFEST.get().replace.get(brk.name, None)
        if isinstance(alias, brick.Brick):
            src = alias
        if src.name not in fst:
            fst[src.name] = brk.name
        elif fst[src.name] != brk.name:
            raise util.UserError(
                f"{src.name} {src.version} used for "
                f"two different brick name ({fst[src.name]} and {brk.name})"
            )

    return used


def directs() -> Iterable[brick.Brick]:
    """Return bricks used directly by target."""
    dirs: MutableSet[brick.Brick] = set()
    _, path = resolve(brick.TARGET.get().name)
    assert path
    for name in imports(path):
        dirs.add(resolve(name)[0])
    return dirs


def resolve(name: str) -> Tuple[brick.Brick, Optional[pathlib.Path]]:
    for brk in brick.BUILD_LIST.get():
        if brk.name == name:
            return brk, fetch(brk)
    if name in brick.MANIFEST.get().replace:
        match = re.match(r".*(v[0-9]+$)", name)
        if match:
            return brick.Brick(name, f"{match.group(1)}.0.0"), None
        return brick.Brick(name, "v0.0.0"), None
    new = latest(name, tuple(brick.MANIFEST.get().exclude))
    if new is None:
        raise util.UserError(f"no version available for {name}")
    return new, None


def imports(path: pathlib.Path) -> Iterable[str]:
    res: Set[str] = set()
    for file in chain.from_iterable([path.glob("**/?*.ic")]):
        if config.HOME_PATH in file.parents and config.HOME_PATH not in path.parents:
            # for when HOME_PATH is inside the current brick directory
            # like for integration tests (local .ic folder)
            continue
        tree = ast.parse(file.read_text(), str(file))
        raw: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                raw.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                if node.level == 0:
                    assert node.module
                    raw.update(
                        ".".join([node.module, alias.name]) for alias in node.names
                    )
        curr = [i.split(".")[0:2] for i in raw if i.partition(".")[0] != "ic"]
        res.update({".".join(i) for i in curr if len(i) == 2 and i[1] != "*"})
    return res


@lru_cache(maxsize=None)
def fetch(brk: brick.Brick) -> pathlib.Path:
    if brk == brick.TARGET.get():
        return brick.ROOT.get()
    repl = brick.MANIFEST.get().replace.get(brk.name, None)
    if not repl or isinstance(repl, brick.Brick):
        return artifact(cast(brick.Brick, repl or brk))
    return brick.ROOT.get().joinpath(repl)


class Reqs:
    # pylint: disable=no-self-use

    def required(self, brk: brick.Brick) -> Iterable[brick.Brick]:
        reqs: Iterable[brick.Brick]
        if brk == brick.TARGET.get():
            reqs = list(brick.BUILD_LIST.get()[1:])
        else:
            repl = brick.MANIFEST.get().replace.get(brk.name, None)
            if repl:
                if not isinstance(repl, brick.Brick):
                    try:
                        reqs = brick.parse(brick.ROOT.get().joinpath(repl)).require
                    except util.UserError as exc:
                        raise util.UserError(
                            f"cannot parse replace {brk.name}: {str(exc)}"
                        )
                else:
                    reqs = manifest(repl).require
            else:
                reqs = manifest(brk).require
        excl = set(brick.MANIFEST.get().exclude)
        res: List[brick.Brick] = []
        for req in reqs:
            while req in excl:
                reqn = after(req)
                if not reqn:
                    raise util.UserError(
                        f"{brk.name} {brk.version} depends on excluded "
                        f"{req.name} {req.version} with no newer version available"
                    )
                req = reqn
            res.append(req)
        return res

    def max(self, ver1: str, ver2: str) -> str:
        if ver1 == "none" or ver2 == "":
            return ver2
        if ver2 == "none" or ver1 == "":
            return ver1
        return ver2 if ver1 < ver2 else ver1

    def upgrade(self, brk: brick.Brick) -> brick.Brick:
        res = latest(brk.name, tuple(brick.MANIFEST.get().exclude))
        assert res
        assert res.version >= brk.version
        return res

    def previous(self, brk: brick.Brick) -> brick.Brick:
        vers = reversed(list(versions(brk.name)))
        ver = next((v for v in vers if v < brk.version), "none")
        return brick.Brick(brk.name, ver)


@lru_cache(maxsize=None)
def versions(name: str) -> Iterable[str]:
    """Return all the known versions for the given brick name."""
    parts = name.split(".")
    vers_url = "/".join(
        [config.PROXY_URL, "indexv1", "users", parts[0], "bricks", parts[1], "versions"]
    )
    req = requests.get(vers_url)
    # pylint: disable=no-member
    code = req.status_code
    if code == requests.codes.not_found:
        raise util.UserError(f"{name} not found in the remote index")
    if code != requests.codes.ok:  # pragma: no cover
        raise util.UserError(f"cannot query {name} versions: [{code}] {req.reason}")
    return tuple(sorted(req.json()))


@lru_cache(maxsize=None)
def latest(name: str, exclude: Sequence[brick.Brick]) -> Optional[brick.Brick]:
    """Return the latest not exclude version of the given brick name."""
    vers = reversed(list(versions(name)))
    ver = next((v for v in vers if brick.Brick(name, v) not in set(exclude)), None)
    return brick.Brick(name, ver) if ver else None


@lru_cache(maxsize=None)
def after(brk: brick.Brick) -> Optional[brick.Brick]:
    """Return the next version after the version of the given brick."""
    vers = versions(brk.name)
    ver = next((v for v in vers if v > brk.version), None)
    return brick.Brick(brk.name, ver) if ver else None


@lru_cache(maxsize=None)
def artifact(brk: brick.Brick) -> pathlib.Path:
    """Search the given brick artifact in the local cache or download it
    and unpack it from the remote index and return its path.

    """
    org, com = brk.name.split(".")
    cache_path = config.CACHE_PATH.joinpath(org, com)
    zip_path = cache_path.joinpath(f"{brk.version}.zip")
    index_path = config.INDEX_PATH.joinpath(org, com, brk.version)
    if not zip_path.exists():
        try:
            cache_path.mkdir(parents=True, exist_ok=True)
            with zip_path.open("wb") as bin_file:
                download_artifact(brk, cast(BinaryIO, bin_file))
        except Exception:
            zip_path.unlink()
            while cache_path != config.CACHE_PATH:
                if os.listdir(cache_path):
                    break
                cache_path.rmdir()
                cache_path = cache_path.parent
            raise
        if index_path.exists():
            shutil.rmtree(index_path)
    if not index_path.exists():
        index_path.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(str(zip_path)) as zip_file:
            zip_file.extractall(str(index_path))
    return index_path


def download_artifact(brk: brick.Brick, file: BinaryIO):
    """Save the content of /bricks/<name>/versions/<version>.zip in the
    given file handler.

    """
    bid = " ".join([brk.name, brk.version])
    LOGGER.info("downloading %s artifact", bid)
    parts = brk.name.split(".")
    zip_url = "/".join(
        [
            config.PROXY_URL,
            "indexv1",
            "users",
            parts[0],
            "bricks",
            parts[1],
            "versions",
            f"{brk.version}.zip",
        ]
    )
    req = requests.get(zip_url, allow_redirects=True, stream=True)
    # pylint: disable=no-member
    code = req.status_code
    if code == requests.codes.not_found:
        raise util.UserError(f"{bid} not found in the remote index")
    if req.status_code != requests.codes.ok:  # pragma: no cover
        raise util.UserError(f"cannot download {bid} artifact: [{code}] {req.reason}")
    for chunk in req.iter_content(chunk_size=8192):
        file.write(chunk)


@lru_cache(maxsize=None)
def manifest(brk: brick.Brick) -> brick.Manifest:
    """Search the given brick manifest in the local cache or download it
    from the remote index and return it.

    """

    org, com = brk.name.split(".")
    cache_path = config.CACHE_PATH.joinpath(org, com)
    json_path = cache_path.joinpath(f"{brk.version}.json")
    if not json_path.exists():
        try:
            cache_path.mkdir(parents=True, exist_ok=True)
            with json_path.open("w") as text_file:
                download_manifest(brk, cast(TextIO, text_file))
        except Exception:
            json_path.unlink()
            while cache_path != config.CACHE_PATH:
                if os.listdir(cache_path):
                    break
                cache_path.rmdir()
                cache_path = cache_path.parent
            raise
    return brick.parse(data=json.loads(json_path.read_text()))


def download_manifest(brk: brick.Brick, file: TextIO):
    """Save the content of /bricks/<name>/versions/<version>.json in the
    given file handler.

    """
    bid = " ".join([brk.name, brk.version])
    parts = brk.name.split(".")
    man_url = "/".join(
        [
            config.PROXY_URL,
            "indexv1",
            "users",
            parts[0],
            "bricks",
            parts[1],
            "versions",
            f"{brk.version}.json",
        ]
    )
    req = requests.get(man_url)
    # pylint: disable=no-member
    code = req.status_code
    if code == requests.codes.not_found:
        raise util.UserError(f"{bid} not found in the remote index")
    if code != requests.codes.ok:  # pragma: no cover
        raise util.UserError(f"cannot download {bid} manifest: [{code}] {req.reason}")
    file.write(req.text)
