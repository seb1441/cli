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
from typing import Mapping, Optional

import botocore.exceptions
import click
import treelib

from ...cloud.aws import encode
from .. import util as cli_util
from . import load, stack


@click.command(name="tree")
@click.option("--params", "overrides", help="Parameter overrides.")
@click.option("--json", "raw", is_flag=True, help="Format output in JSON.")
@click.argument("name", metavar="brick", required=False)
@click.argument("version", metavar="version", required=False)
@click.pass_context
def cmd(
    ctx,
    name: Optional[str],
    version: Optional[str],
    *,
    raw: bool,
    overrides: Optional[str],
):
    """Display the hierarchy of the brick."""
    s3_bucket, s3_prefix = ctx.obj["s3_bucket"], ctx.obj["s3_prefix"]
    if not s3_bucket:
        # when invoking `ic aws tree`, the s3_bucket is not meaningful
        s3_bucket = "<not provided>"
    if name and all(c not in name for c in (".", ":")):
        if version:
            raise click.BadArgumentUsage(f"Got unexpected extra argument ({version})")
        try:
            tree = stack.Stack(name).tree
        except botocore.exceptions.ClientError as exc:
            raise cli_util.UserError(f"aws: {exc}")
    else:
        node, _ = load.execute("brick", name, version, overrides, s3_bucket, s3_prefix)
        tree = encode.Template(node).tree
    if raw:
        click.echo(json.dumps(tree))
    else:
        click.echo(format_tree(tree))


def format_tree(data: Mapping) -> str:
    tree = treelib.Tree()
    _format_tree(tree, data)
    return str(tree).strip("\n")


def _format_tree(tree: treelib.Tree, data: Mapping, parent=None):
    text = data["name"]
    if "type" in data:
        text += " " + click.style(data["type"], dim=True)
    parent = tree.create_node(text, data["id"], parent)
    for child in data.get("children", []):
        _format_tree(tree, child, parent)
