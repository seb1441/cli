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
from typing import Optional, cast

import click

from ...cloud.aws import config, encode
from ...cloud.aws import util as aws_util
from .. import brick
from . import load, util


@click.command(name="dump")
@click.option("--params", "overrides", help="Parameter overrides.")
@click.option("--upload", is_flag=True, help="Upload artifacts to S3.")
@click.option("--pretty", is_flag=True)
@click.argument("name", metavar="brick", required=False)
@click.argument("version", metavar="version", required=False)
@click.argument("idn", metavar="name", required=False)
@click.pass_context
def cmd(
    ctx,
    name: Optional[str],
    version: Optional[str],
    idn: Optional[str],
    *,
    overrides: Optional[str],
    upload: bool,
    pretty: bool,
):
    """Dump raw AWS CloudFormation artifacts."""
    s3_bucket, s3_prefix = ctx.obj["s3_bucket"], ctx.obj["s3_prefix"]
    node, _ = load.execute(idn, name, version, overrides, s3_bucket, s3_prefix)
    tpl = encode.Template(node)
    build = brick.ROOT.get(pathlib.Path.cwd()) / "build"
    build.mkdir(exist_ok=True)
    tpl_path = build / "template.json"
    tpl_path.write_text(tpl.dumps(pretty))
    par_path = build / "parameters.json"
    par_path.write_text(tpl.dumps_params(pretty))
    ass_path = build / "assets.json"
    ass_path.write_text(tpl.dumps_assets(pretty))
    if upload:
        # pylint: disable=protected-access
        artifacts = [(tpl_path, aws_util.asset_info(tpl_path))]
        artifacts += [
            (a._path, cast(aws_util.AssetInfo, a)) for a in config.ASSETS.get()
        ]
        util.upload(artifacts)
