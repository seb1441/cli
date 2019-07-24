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

import logging
import os
import pathlib
import tempfile

import click

from .. import config as core_config
from . import cmd_update, stack

LOGGER = logging.getLogger(__name__)

BRICK_TEMPLATE = """
name: iccli.setup
version: v0.1.0
private: true
main: :brick
""".lstrip()

INDEX_TEMPLATE = """
from ic import aws

@resource
def brick():
    artifacts_bucket = aws.s3.bucket("artifacts_bucket")
    artifacts_bucket.deletion = "retain"
    return dict(
        artifacts_bucket=artifacts_bucket
    )
""".lstrip()


@click.command(name="setup")
@click.argument("hint", default="default")
@click.pass_context
def cmd(ctx, hint: str):
    """Setup the AWS account for the cli."""
    profile, region = ctx.obj["profile"], ctx.obj["region"]
    s3_prefix = ctx.obj["s3_prefix"]
    name = f"ic_setup_{hint}"
    stk = stack.Stack(name)
    if not stk.exists:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = pathlib.Path(tmp)
            (cwd / "brick.yaml").write_text(BRICK_TEMPLATE)
            (cwd / "index.ic").write_text(INDEX_TEMPLATE)
            os.chdir(cwd)
            ctx.invoke(cmd_update.cmd, idn=name)
    s3_bucket = stk.value["artifacts_bucket"]["ref"]
    cfg = core_config.CONFIG.get()[core_config.PROFILE.get()]
    if profile != "default":
        cfg["aws_profile"] = profile
    cfg["aws_region"] = region
    cfg["aws_s3_bucket"] = s3_bucket
    if s3_prefix:
        cfg["aws_s3_prefix"] = s3_prefix
    core_config.save()
