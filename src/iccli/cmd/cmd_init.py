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

import pathlib
from contextlib import suppress
from typing import Any

import click

from . import brick, load, util

INDEX_TEMPLATE = """
@resource
def brick():
    ...
"""


@click.command(name="init")
@click.option("--name", metavar="brick", hidden=True)
def cmd(*, name):
    """Create a new or update the existing brick."""
    cwd = pathlib.Path.cwd()
    man = None
    with suppress(FileNotFoundError):
        load.init(cwd)
        load.load()
        man = brick.MANIFEST.get(None)
    while True:
        name = _prompt("name", brick.check_name, name or getattr(man, "name", None))
        ver = _prompt("version", brick.check_version, getattr(man, "version", "v0.1.0"))
        try:
            brick.check_id(name, ver)
        except util.UserError as exc:
            click.secho(str(exc), fg="red", err=True)
            continue
        priv_def = "true" if getattr(man, "private", False) else "false"
        priv = False

        def check_priv(val: Any):
            if val not in {"true", "false"}:
                raise util.UserError(
                    "invalid private: expected either 'true' or 'false'"
                )
            nonlocal priv
            priv = val == "true" or False
            brick.check_private(priv)

        _prompt("private", check_priv, priv_def)
        licn = getattr(man, "license", None)
        if not priv:
            licn = _prompt("license", brick.check_license, licn or "MIT")
        break
    if man:
        man.name = name
        man.version = ver
        man.license = licn
        man.private = priv
    else:
        brick.MANIFEST.set(brick.Manifest(name, ver, licn, priv))
        brick.TARGET.set(brick.Brick(name, ""))
        brick.ROOT.set(cwd)
        brick.BUILD_LIST.set([brick.TARGET.get()])
        if next(cwd.iterdir(), None) is None:
            cwd.joinpath("index.ic").write_text(INDEX_TEMPLATE.lstrip())
    load.save(set())


def _prompt(text, validator, default=None):
    while True:
        val = click.prompt(text, default=default)
        try:
            validator(val)
            return val
        except util.UserError as exc:
            click.secho(str(exc), fg="red", err=True)
