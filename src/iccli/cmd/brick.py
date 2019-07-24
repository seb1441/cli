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

import importlib.resources
import json
import keyword
import logging
import pathlib
import re
from contextvars import ContextVar
from dataclasses import dataclass, field
from itertools import chain
from typing import (Any, Iterable, List, Mapping, MutableMapping, NamedTuple,
                    Optional, Set, Union)

import semver
from ruamel.yaml import YAML, YAMLError

from . import util

LOGGER = logging.getLogger(__name__)

LICENSES: Set[str] = set(
    json.loads(importlib.resources.read_text(__package__, "licenses.json"))
)

RESERVED = {"assets", "brick", "ic", "icp", "index", "resource"}

MANIFEST: ContextVar["Manifest"] = ContextVar("manifest")
TARGET: ContextVar["Brick"] = ContextVar("target")
ROOT: ContextVar[pathlib.Path] = ContextVar("root")
BUILD_LIST: ContextVar[List["Brick"]] = ContextVar("build_list")


class Brick(NamedTuple):
    """Brick is defined by a brick name and version pair."""

    # A name is in the form of namespace.component
    name: str

    # A version is usually a semantic version in canonical form
    # (e.g. v1.0.0). There are two exceptions to this general rule:
    # First the toplevel target of a build has no specific version and
    # uses version = "".
    # Second, during MVS calculations, the version "none" is used to
    # represent the decision to take no version of a given module.
    version: str


@dataclass
class Manifest:
    """Parsed and interpreted form of a brick.yaml file."""

    name: str
    version: str
    license: Optional[str] = None
    private: bool = False
    description: str = ""
    main: str = ":brick"

    require: Iterable[Brick] = field(default_factory=list)
    replace: Mapping[str, Union[Brick, pathlib.Path]] = field(default_factory=dict)
    exclude: Iterable[Brick] = field(default_factory=list)

    assets: Set[pathlib.Path] = field(default_factory=set)


def check_name(val: Any):
    """Check that the brick name is valid.

    It must be in the form '{namespace}.{component}'.

    """
    err = None
    if not val:
        err = "valid name required"
    elif not isinstance(val, str):
        err = "must be a string"
    elif val.startswith("."):
        err = "relative name not allowed"
    elif any(c.isupper() for c in val):
        err = "mixed case, expected lowercase"
    elif not re.fullmatch(r"[a-z0-9_\.]+", val):
        err = "invalid chars, expected [a-z0-9_.]"
    elif not re.fullmatch(r"[^.]+\.[^.]+", val):
        err = "invalid format, expected 'namespace.component'"
    elif any(v[0].isdigit() for v in val.split(".")):
        err = "parts cannot start with digits"
    elif any(keyword.iskeyword(v) for v in val.split(".")):
        err = "parts cannot contain python keywords"
    elif any(v in RESERVED for v in val.split(".")):
        err = f"parts cannot contain reserved keywords: {RESERVED}"
    elif not all(3 <= len(v) <= 20 for v in val.split(".")):
        err = f"parts must have at least 3 and at most 20 chars"
    if err:
        raise util.UserError(f"malformed brick name {val!r}: {err}")


def check_version(val: Any):
    """Check that the brick version is valid.

    It must be of the form of 'v{semantic version}'.

    """
    err = None
    if not val:
        err = "valid version required"
    elif not isinstance(val, str):
        err = "must be a string"
    elif not val.startswith("v"):
        err = "missing 'v' prefix"
    else:
        try:
            ver = semver.VersionInfo.parse(val[1:])
        except ValueError:
            err = "invalid format, expected semantic version"
        if not err and ver.build:
            err = "build metadata not supported"
    if err:
        raise util.UserError(f"malformed brick version {val!r}: {err}")


def check_id(name: Any, version: Any):
    """Check that the brick name and version pair is valid.

    In addition to the name being a valid brick name and the version
    being a valid semantic version, the two must correspond.
    For example the name org.comv2 only corresponds to semantic versions
    beginning with v2.

    """
    check_name(name)
    check_version(version)
    assert len(version) > 1
    ver = semver.VersionInfo.parse(version[1:])
    if ver.major > 1 and not name.endswith(f"v{ver.major}"):
        raise util.UserError(
            f"mismatched brick name {name!r} and version "
            f"{version!r} (want v{ver.major!r})"
        )
    if ver.major <= 1 and not name[-1].islower() or name[-1] == "v":
        raise util.UserError(
            f"malformed brick name {name!r}: expected to end with a letter != 'v'"
        )


def check_private(val: Any):
    """Check that the brick's private property is a valid boolean."""
    if not isinstance(val, bool):
        raise util.UserError("invalid private: expected a boolean")


def check_license(val: Any, private: bool = False):
    """Check that the brick license is valid.

    It must a valid SPDX identifier.

    """
    err = None
    if private:
        if not isinstance(val, str):
            err = "must be a string"
    else:
        if not val:
            err = "valid license required"
        elif not isinstance(val, str):
            err = "must be a string"
        elif val not in LICENSES:
            err = "unknown, expected SPDX"
    if err:
        raise util.UserError(f"malformed brick license {val!r}: {err}")


def check_description(val: Any):
    """Check that the brick description is valid.

    It must be no longer that 140 characters.

    """
    err = None
    if not isinstance(val, str):
        err = "must be a string"
    elif len(val) > 140:
        err = "too long, must be < 140 characters"
    if err:
        raise util.UserError(f"malformed brick description {val!r}: {err}")


def check_main(val: Any):
    """Check that the brick entrypoint is valid.

    It must be of the form '.path.parts:definition'.

    """
    err = None
    if not val:
        err = "valid main required"
    elif not isinstance(val, str):
        err = "must be a string"
    elif not val.startswith(".") and not val.startswith(":"):
        err = "must be a relative path"
    elif not re.fullmatch(r"[a-z0-9_\.]*:[a-z0-9_]+", val):
        err = "invalid format, expected 'path:definition'"
    if err:
        raise util.UserError(f"malformed brick main {val!r}: {err}")


def parse(root: pathlib.Path = None, data: Mapping = None) -> Manifest:
    """Extract the brick.yaml's info from the given directory."""
    yaml = YAML()
    if not data:
        assert root
        file = root.joinpath("brick.yaml")
        if not file.exists():  # pragma: no cover
            raise FileNotFoundError("brick.yaml not found")
        try:
            raw = file.read_text()
            data = yaml.load(raw) or {}
        except YAMLError as exc:
            LOGGER.error("%s:\n%s", str(file), str(exc))
            raise util.UserError("cannot parse brick.yaml")
    allowed_keys: Set[str] = {
        "name",
        "description",
        "version",
        "license",
        "private",
        "main",
        "require",
        "replace",
        "exclude",
        "assets",
    }
    unknown_keys = set(data.keys()) - allowed_keys
    if unknown_keys:
        raise util.UserError(f"unknown properties: {', '.join(unknown_keys)}")
    name, ver = data.get("name", ""), data.get("version", "")
    check_id(name, ver)
    priv = data.get("private", False)
    check_private(priv)
    licn = data.get("license")
    if not priv:
        check_license(licn, priv)
    desc = re.sub(r"\s+", " ", data.get("description", "")).strip()
    check_description(desc)
    main = data.get("main", "")
    check_main(main)
    raw_req = data.get("require", {})
    if not isinstance(raw_req, dict):
        raise util.UserError("invalid require: expected a dictionary")
    req: List[Brick] = []
    for key, val in raw_req.items():
        curr = {key: val}
        try:
            check_id(key, val)
        except util.UserError as exc:
            raise util.UserError(f"invalid require {curr!r}: {str(exc)}")
        req.append(Brick(key, val))
    raw_repl = data.get("replace", {})
    if not isinstance(raw_repl, dict):
        raise util.UserError("invalid replace: expected a dictionary")
    repl: MutableMapping[str, Union[Brick, pathlib.Path]] = {}
    for key, val in raw_repl.items():
        curr = {key: val}
        try:
            check_name(key)
        except util.UserError as exc:
            raise util.UserError(f"invalid replace {curr!r}: {str(exc)}")
        if not isinstance(val, str):
            raise util.UserError(
                f"invalid replace {curr!r}: "
                f"expected either a path or {{'name': 'version'}}"
            )
        if " " in val:
            parts = val.partition(" ")
            try:
                check_id(parts[0], parts[-1])
            except util.UserError as exc:
                raise util.UserError(f"invalid replace {val!r}: {str(exc)}")
            repl[key] = Brick(parts[0], parts[-1])
        else:
            repl[key] = pathlib.Path(val)
    raw_exc = data.get("exclude", {})
    if not isinstance(raw_exc, dict):
        raise util.UserError("invalid exclude: expected a dictionary")
    excl: List[Brick] = []
    for key, val in raw_exc.items():
        curr = {key: val}
        try:
            check_id(key, val)
        except util.UserError as exc:
            raise util.UserError(f"invalid exclude {curr!r}: {str(exc)}")
        excl.append(Brick(key, val))
    ass: Set[pathlib.Path] = set()
    if root:
        raw_ass = data.get("assets", [])
        if not isinstance(raw_ass, list):
            raise util.UserError("invalid assets: expected a list")
        ass = set(chain.from_iterable(root.glob(a) for a in raw_ass))
    return Manifest(name, ver, licn, priv, desc, main, req, repl, excl, ass)
