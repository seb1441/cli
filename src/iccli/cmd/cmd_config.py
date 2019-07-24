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

import click

from . import config


@click.command(name="config")
def cmd():
    """Create a new or update the existing config."""
    _config, _profile = config.CONFIG.get(), config.PROFILE.get()
    if _profile not in _config:
        _config.add_section(_profile)
    cfg = _config[_profile]
    for key in ("aws_profile", "aws_region", "aws_s3_bucket", "aws_s3_prefix"):
        val = click.prompt(key.replace("_", " "), cfg.get(key, ""))
        if val:
            cfg[key] = val
    config.save()
