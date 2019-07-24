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

import urllib.parse

import arrow
import click
import requests

from . import config, util


@click.command(name="search")
@click.option("--author", help="Filter by author.")
@click.option("--license", "license_", help="Filter by license.")
@click.argument("query", required=False, nargs=-1)
def cmd(query=None, *, author=None, license_=None):
    """Search for bricks in the index."""
    params = dict()
    if query:
        params.update(query=" ".join(query))
    if author:
        params.update(author=author)
    if license_:
        params.update(license=license_)
    search_url = f"{config.PROXY_URL}/indexv1/search?{urllib.parse.urlencode(params)}"
    with requests.get(search_url) as req:
        req.raise_for_status()
        res = req.json()
    if not res:
        raise util.UserError("no result found")

    if res:
        click.secho("─" * 70, dim=True)
    for data in res:
        click.secho(data["name"], bold=True)
        desc = data["description"]
        if desc:
            click.secho("\n".join([desc[:70], desc[70:]]), fg="blue")
        else:
            click.secho()
            click.secho()
        date = arrow.get(int(data["timestamp"])).humanize()
        click.secho(
            f"{data['license']} • {data['version']} • {date}", fg="yellow", dim=True
        )
        click.secho("─" * 70, dim=True)
