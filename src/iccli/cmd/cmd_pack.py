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
import pathlib
import zipfile

import click

from . import brick, config, load, util

LOGGER = logging.getLogger(__name__)


@click.command(name="pack")
def cmd():
    """Create zip archive of the current brick."""
    try:
        load.init(pathlib.Path.cwd())
    except FileNotFoundError:
        raise util.UserError("brick.yaml not found")
    used = {b.name for b in load.load()}
    file = brick.ROOT.get() / "brick.zip"
    pack(file)
    load.save(used)


def pack(file):
    root = brick.ROOT.get()
    paths = set()
    for path in map(root.glob, ["**/?*.ic", "brick.yaml", "LICENSE", "README.md"]):
        paths.update(path)
    paths.update(brick.MANIFEST.get().assets)
    paths = {p for p in paths if config.INDEX_PATH not in p.parents}
    with zipfile.ZipFile(file, "w") as zip_file:
        for path in sorted(p.relative_to(root) for p in paths):
            LOGGER.info("adding: %s", str(path))
            info = zipfile.ZipInfo.from_file(path)  # type: ignore
            info.date_time = (2013, 2, 21, 0, 3, 2)
            info.external_attr = 0o444 << 16
            zip_file.writestr(  # type: ignore
                info,
                path.read_bytes(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )
