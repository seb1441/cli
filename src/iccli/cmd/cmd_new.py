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

import os
import pathlib

import click

from . import brick, cmd_init, util


@click.command(name="new")
@click.argument("name", metavar="brick")
@click.pass_context
def cmd(ctx, name):
    """Create a new folder and init a new brick."""
    brick.check_name(name)
    cwd = pathlib.Path.cwd() / name.rpartition(".")[-1]
    if cwd.exists():
        raise util.UserError(f"{cwd.name} directory already exists")
    cwd.mkdir()
    os.chdir(cwd)
    ctx.forward(cmd_init.cmd, name=name)
