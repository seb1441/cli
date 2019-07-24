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

import click

from . import brick, load, mvs, util


@click.command(name="update")
@click.argument("name", metavar="brick", required=False)
@click.argument("version", metavar="version", required=False)
@click.option("--tidy", is_flag=True, help="Add missing and remove unused bricks.")
@click.option("--remove", is_flag=True, help="Remove the given brick.")
def cmd(name, version, tidy, remove):
    """Update requirements."""
    try:
        load.init(pathlib.Path.cwd())
    except FileNotFoundError:
        raise util.UserError("brick.yaml not found")
    used = {b.name for b in load.load()}
    if tidy:
        if name or version:
            raise click.UsageError("Got unexpected extra arguments")
        load.save(used)
        return
    if remove:
        if version:
            raise click.UsageError("Got unexpected extra argument (version)")
        if name in used:
            raise util.UserError(f"cannot remove used brick {name!r}")
        brk = brick.Brick(name, "none")
        build = mvs.downgrade(brick.TARGET.get(), load.Reqs(), brk)
        brick.BUILD_LIST.set(build)
        load.save(used)
        return
    if not name and not version:
        brick.BUILD_LIST.set(mvs.upgrade_all(brick.TARGET.get(), load.Reqs()))
    else:
        if not version:
            brick.check_name(name)
            brk = load.latest(name, tuple(brick.MANIFEST.get().exclude))
            if not brk:
                raise util.UserError(f"no version available for {name}")
        else:
            brick.check_id(name, version)
            brk = brick.Brick(name, version)
        for known in brick.BUILD_LIST.get():
            if known.name == brk.name:
                if known.version > brk.version:
                    build = mvs.downgrade(brick.TARGET.get(), load.Reqs(), brk)
                    brick.BUILD_LIST.set(build)
                elif known.version < brk.version:
                    build = mvs.upgrade(brick.TARGET.get(), load.Reqs(), brk)
                    brick.BUILD_LIST.set(build)
                break
        else:
            brick.BUILD_LIST.get().append(brk)
            used.add(brk.name)
            brick.BUILD_LIST.set(mvs.build_list(brick.TARGET.get(), load.Reqs()))
    load.save(used)
