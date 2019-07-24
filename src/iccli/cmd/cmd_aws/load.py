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

import importlib
import inspect
import logging
import pathlib
import sys
from collections import ChainMap, defaultdict
from contextlib import suppress
from functools import partial
from typing import Callable, Dict, Mapping, Optional, Tuple, cast

import click

from ...cloud.aws import config as aws_config
from ...cloud.aws import importer as aws_importer
from ...cloud.aws import resources
from ...cloud.aws.resources import importer as rescs_importer
from ...core import config as core_config
from ...core import importer as core_importer
from .. import brick
from .. import config as cli_config
from .. import load
from .. import util as cli_util

LOGGER = logging.getLogger(__name__)


def definition(name: Optional[str], version: Optional[str]) -> Callable:
    if name and name.partition(".")[0] == "ic":
        mode_token = core_config.MODE.set(core_config.Mode.IC)
        sys.meta_path.insert(0, rescs_importer.Finder())
        meta_paths = 1
        name = f"icl{name[len('ic'):]}"
        brick.check_main(f".{name}")
        path, _, defn = name.partition(":")
        save = False
    else:
        if not name or any(name.startswith(c) for c in (".", ":")):
            if version:
                raise click.BadArgumentUsage(
                    f"Got unexpected extra argument ({version})"
                )
            cwd = pathlib.Path.cwd()
            save = True
        else:
            path = name.partition(":")[0]
            idn = ".".join(path.split(".")[0:2])
            if version:
                brick.check_id(idn, version)
                cwd = load.artifact(brick.Brick(idn, version))
            else:
                brick.check_name(idn)
                cwd = load.artifact(load.latest(idn, ()))
            name = name[len(idn) :]
            save = False
        try:
            load.init(cwd)
        except FileNotFoundError:
            raise cli_util.UserError("brick.yaml not found")
        if not name:
            name = brick.MANIFEST.get().main
        else:
            brick.check_main(name)
        loaded = load.load()
        index: Dict[str, Dict[str, brick.Brick]] = defaultdict(dict)
        for brk in loaded:
            if brk.version:
                parts = brk.name.split(".")
                index[parts[0]][parts[1]] = brk
        mode_token = core_config.MODE.set(core_config.Mode.IC)
        sys.meta_path.insert(0, core_importer.LibFinder())
        sys.meta_path.insert(1, rescs_importer.Finder())
        sys.meta_path.insert(
            2,
            core_importer.Finder(
                "icm",
                ".ic",
                "index",
                partial(_resolve_local, brick.ROOT.get()),
                aws_importer.Loader,
            ),
        )
        sys.meta_path.insert(
            3,
            core_importer.Finder(
                "icx",
                ".ic",
                "index",
                partial(_resolve_index, index),
                aws_importer.Loader,
            ),
        )
        meta_paths = 4
        path, _, defn = name.partition(":")
        path = path if path.startswith(".") else f".{path}"
    try:
        mod = importlib.import_module(path, "icm")
        func = getattr(mod, defn)
    finally:
        core_config.MODE.reset(mode_token)
        del sys.meta_path[0:meta_paths]
    if save:
        load.save({b.name for b in loaded})
    return func


def parameters(defn: Callable, overrides: Optional[str]) -> Mapping:
    _overrides: Mapping = {}
    if overrides:
        _overrides = dict(
            cast(Tuple[str, str], map(str.strip, p.strip().split("=")))
            for p in overrides.split(",")
        )
    root = pathlib.Path.cwd()
    if not (root / "params.icp").exists():
        with suppress(FileNotFoundError):
            load.init(root)
            root = brick.ROOT.get()
    mode_token = core_config.MODE.set(core_config.Mode.ICP)
    sys.meta_path.insert(0, core_importer.LibFinder())
    sys.meta_path.insert(
        1,
        core_importer.Finder(
            "icpm", ".icp", "params", partial(_resolve_local, root), aws_importer.Loader
        ),
    )
    try:
        mod = importlib.import_module(".", "icpm")
        chain = ChainMap({k: v for k, v in vars(mod).items() if not k.startswith("_")})
        chain = chain.new_child(_overrides)
        res = dict(chain)
        sig = list(inspect.signature(defn).parameters.items())
        if all(p[1].kind != inspect.Parameter.VAR_KEYWORD for p in sig):
            res = {name: res[name] for name, _ in sig if name in res}
    finally:
        core_config.MODE.reset(mode_token)
        del sys.meta_path[0:2]
    return res


def execute(
    idn: Optional[str],
    name: Optional[str],
    version: Optional[str],
    overrides: Optional[str],
    s3_bucket: Optional[str],
    s3_prefix: Optional[str],
) -> Tuple[resources.Resource, str]:
    if name and all(c not in name for c in (".", ":")):
        if version or idn:
            extra = [a for a in [version, idn] if a]
            raise click.BadArgumentUsage(
                f"Got unexpected extra arguments ({', '.join(extra)})"
            )
        idn, name = name, None
    elif version and "." not in version:
        if idn:
            raise click.BadArgumentUsage(f"Got unexpected extra argument ({idn})")
        idn, version = version, None
    if not idn:
        raise click.MissingParameter(param_hint='"name"', param_type="argument")
    aws_config.SENSITIVES.set(list())
    aws_config.ASSETS.set(set())
    aws_config.S3_BUCKET.set(s3_bucket or "<not provided>")
    aws_config.S3_PREFIX.set(s3_prefix or "")
    defn = definition(name, version)
    params = parameters(defn, overrides)
    node = defn(idn, **params)
    used_assets = aws_config.ASSETS.get()
    if brick.TARGET.get(brick.Brick("", "")).name:
        decl_assets = brick.MANIFEST.get().assets
        for asset in used_assets:
            if not s3_bucket:
                raise cli_util.UserError("missing aws s3 bucket")
            path = asset._path  # pylint: disable=protected-access
            if cli_config.HOME_PATH not in path.parents and path not in decl_assets:
                raise cli_util.UserError(f"asset used but not declared: {path}")
    return node, idn


def _resolve_local(
    root: pathlib.Path, parent: Optional[pathlib.Path], name: str
) -> Optional[pathlib.Path]:
    if parent is None:
        return root
    return parent.joinpath(name.rpartition(".")[-1])


def _resolve_index(
    index: Dict[str, Dict[str, brick.Brick]], parent: Optional[pathlib.Path], name: str
) -> Optional[pathlib.Path]:
    dots = name.count(".")
    if parent is None and not dots:
        return cli_config.INDEX_PATH
    if dots == 0:
        if name not in index:  # pragma: no cover
            raise LookupError  # already catched by load.load
        return None
    if dots == 1:
        parts = name.split(".")
        nsp = index[parts[0]]
        if parts[1] not in nsp:  # pragma: no cover
            raise LookupError  # already catched by load.load
        return load.fetch(nsp[parts[1]])
    assert parent
    return parent.joinpath(name.rpartition(".")[-1])
