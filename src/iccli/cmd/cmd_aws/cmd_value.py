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

import json

import botocore.exceptions
import click

from ..util import UserError
from . import stack


@click.command(name="value")
@click.argument("name", metavar="brick")
def cmd(name: str):
    """Display the value of the brick."""
    try:
        stk = stack.Stack(name)
        click.echo(json.dumps(stk.value))
    except botocore.exceptions.ClientError as exc:
        raise UserError(f"aws: {exc}")
