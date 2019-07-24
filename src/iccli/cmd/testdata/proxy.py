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

import importlib.resources
import io
import re
import socket
import zipfile
from functools import partial

import flask
import pytest
import pytest_flask.fixtures
from ruamel.yaml import YAML

from .. import brick, txtar
from . import brick as brick_fixture


@pytest.fixture
def proxy_app():
    """Start the IC brick proxy on a random localhost port.

    The proxy serves from testdata/brick.

    """
    # pylint: disable=unused-variable
    infos = importlib.resources.contents(brick_fixture)
    infos = filter(lambda i: i.endswith(".txt"), infos)
    infos = map(lambda i: re.sub(r".txt$", "", i), infos)
    bricks = []
    for i in infos:
        path, _, version = i.rpartition("_")
        brick.check_id(path, version)
        bricks.append(brick.Brick(path, version))
    app = flask.Flask(__name__)

    app.add_url_rule("/", "index", index)
    app.add_url_rule(
        "/indexv1/users/<user>/bricks/<com>/versions",
        "versions",
        partial(versions, bricks),
        methods=["GET"],
    )
    app.add_url_rule(
        "/indexv1/users/<user>/bricks/<com>/versions/<version>.json",
        "manifest",
        partial(manifest, bricks),
        methods=["GET"],
    )
    app.add_url_rule(
        "/indexv1/users/<user>/bricks/<com>/versions/<version>.zip",
        "archive",
        partial(archive, bricks),
        methods=["GET"],
    )
    return app


def index():
    return flask.Response(status=204)


def versions(bricks, user, com):
    res = []
    for brk in bricks:
        if brk.name == f"{user}.{com}":
            res.append(brk.version)
    if res:
        return flask.jsonify(res)
    return flask.Response(status=404)


def manifest(bricks, user, com, version):
    yaml = YAML()
    arc = _read_archive(bricks, user, com, version)
    if not arc:
        return flask.Response(status=404)
    for file in arc.files:
        if file.name == "brick.yaml":
            return flask.jsonify(yaml.load(file.data))
    raise TypeError("no .json file in archive")


def archive(bricks, user, com, version):
    arc = _read_archive(bricks, user, com, version)
    if not arc:
        return flask.Response(status=404)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED) as zip_file:
        for file in filter(lambda f: not f.name.startswith("."), arc.files):
            info = zipfile.ZipInfo(file.name)
            zip_file.writestr(info, file.data)
    buf.seek(0)
    return flask.send_file(buf, mimetype="application/zip")


def _read_archive(bricks, user, com, version):
    key = f"{user}.{com}"
    for brk in bricks:
        if brk.name == key and brk.version == version:
            return txtar.parse(
                importlib.resources.read_text(brick_fixture, f"{key}_{version}.txt")
            )
    return None


@pytest.fixture(scope="function")
def proxy(request, proxy_app, monkeypatch):
    """Run proxy app in a separate process."""
    # pylint: disable=redefined-outer-name
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("", 0))
    port = sock.getsockname()[1]
    sock.close()

    host = "localhost"
    monkeypatch.setitem(proxy_app.config, "SERVER_NAME", ":".join([host, str(port)]))

    server = pytest_flask.fixtures.LiveServer(proxy_app, host, port)
    server.start()
    request.addfinalizer(server.stop)
    return server
