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

import http.client
import json
import logging
import pathlib
import tempfile

import click
import requests
from ruamel.yaml import YAML

from . import auth, brick, cmd_pack, config, load, util

LOGGER = logging.getLogger(__name__)
DISCLAIMER = """
To avoid breaking projects that may depend on your bricks, ic.dev index
does not support brick deletion or deleting a version of a brick. Under
special circumstances, such as for legal reasons or to conform with GDPR
standards, you can request deleting a brick through ic.dev support.
"""


@click.command(name="publish")
def cmd():
    """Publish the current brick to the index."""
    # pylint: disable=bare-except
    accept_key = "accept_publish_terms"
    accept = config.CONFIG.get()["default"].get(accept_key)
    if accept != "yes":
        click.echo(DISCLAIMER)
        click.confirm("Do you agree?", abort=True)
        config.CONFIG.get()["default"][accept_key] = "yes"
        config.save()
    try:
        load.init(pathlib.Path.cwd())
    except FileNotFoundError:
        raise util.UserError("brick.yaml not found")
    used = {b.name for b in load.load()}
    load.save(used)
    auth.load()
    if auth.STATE.get() != auth.State.AUTH:
        raise util.UserError("login required")
    base = config.PROXY_URL
    man = brick.MANIFEST.get()
    user, com = man.name.split(".")
    ver = man.version
    create_url = f"{base}/indexv1/users/{user}/bricks/{com}/versions/{ver}"
    yaml = YAML()
    data = json.dumps(yaml.load((brick.ROOT.get() / "brick.yaml").read_text()))
    headers = dict(Authorization=auth.ID_TOKEN.get())
    with requests.post(create_url, data=data, headers=headers) as req:
        if req.status_code != 200:
            code = http.client.responses[req.status_code]
            try:
                msg = req.json()["message"]
            except:
                msg = req.text
            raise util.UserError(f"{code}: {msg}")
        info = req.json()
    with tempfile.SpooledTemporaryFile() as tmp_file:
        cmd_pack.pack(tmp_file)
        tmp_file.seek(0)
        files = dict(file=tmp_file)
        with requests.post(info["url"], data=info["fields"], files=files) as req:
            req.raise_for_status()
