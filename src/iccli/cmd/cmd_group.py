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
import logging
import platform
import sys
from typing import List, Optional

import click
import pkg_resources

from . import (
    auth,
    cmd_config,
    cmd_fetch,
    cmd_init,
    cmd_login,
    cmd_logout,
    cmd_new,
    cmd_pack,
    cmd_publish,
    cmd_search,
    cmd_update,
    config,
    util,
)
from .cmd_aws import cmd_group as cmd_group_aws

LOGGER = logging.getLogger(__name__)


def version():
    return json.dumps(
        {
            "%(prog)s": pkg_resources.require("iccli")[0].version,
            "python": platform.python_version(),
            platform.system().lower(): platform.release(),
            "boto3": pkg_resources.require("boto3")[0].version,
        },
        indent=2,
    )


@click.group(name="ic")
@click.option("--debug", flag_value=logging.DEBUG, help="Show all debug logs.")
@click.option("--profile", default="default", help="Config profile to use.")
@click.pass_context
@click.version_option(message=version())
def cmd(ctx, *, debug, profile):
    """Bricks and mortar for cloud developers."""
    util.configure_logger(debug or logging.INFO)
    config.load(profile)
    sub = ctx.invoked_subcommand
    if profile not in config.CONFIG.get() and sub not in ("config", "aws"):
        raise util.UserError(f"config profile {profile!r} not found")
    if sub != "login":
        auth.load()
    ctx.default_map = dict()


cmd.add_command(cmd_config.cmd)
cmd.add_command(cmd_new.cmd)
cmd.add_command(cmd_init.cmd)
cmd.add_command(cmd_fetch.cmd)
cmd.add_command(cmd_update.cmd)
cmd.add_command(cmd_login.cmd)
cmd.add_command(cmd_logout.cmd)
cmd.add_command(cmd_pack.cmd)
cmd.add_command(cmd_publish.cmd)
cmd.add_command(cmd_search.cmd)
cmd.add_command(cmd_group_aws.cmd)


def main(args: Optional[List[str]] = None):
    # pylint: disable=broad-except
    exit_code = 1
    try:
        cmd.main(prog_name="ic", args=args, standalone_mode=False)
        exit_code = 0
    except util.UserError as exc:
        LOGGER.error(str(exc))
    except click.Abort:  # pragma: no cover
        LOGGER.error("Aborted!")
    except click.ClickException as exc:
        exc.show()
        exit_code = exc.exit_code
    except Exception as exc:  # pragma: no cover
        LOGGER.exception(exc)
    sys.exit(exit_code)
