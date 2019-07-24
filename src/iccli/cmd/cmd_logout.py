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
import logging
import threading
import time
import urllib.parse
import webbrowser

import click
import flask
import werkzeug.serving

from . import auth, util

LOGGER = logging.getLogger(__name__)


@click.command(name="logout")
@click.option(
    "--manual", is_flag=True, help="Paste links into your browser by yourself."
)
def cmd(*, manual: bool):
    """Log out from ic.dev"""
    if auth.STATE.get() < auth.State.INIT:
        raise util.UserError("cannot init auth module")
    params = dict(
        client_id=auth.CLIENT_ID, logout_uri="http://localhost:21213/callback"
    )
    logout_url = f"{auth.AUTH_URL}/logout?{urllib.parse.urlencode(params)}"

    app = flask.Flask(__name__)
    logger = logging.getLogger("werkzeug")
    logger.setLevel(logging.ERROR)

    class Server(threading.Thread):
        def __init__(self):
            super().__init__()
            self.server = werkzeug.serving.make_server("0.0.0.0", 21213, app)

        def run(self):
            self.server.serve_forever()

        def shutdown(self):
            self.server.shutdown()

    terminate = False

    @app.route("/callback")
    def callback():  # pylint: disable=unused-variable
        nonlocal terminate
        terminate = True
        return importlib.resources.read_text(__package__, "callback.html")

    if manual:
        click.echo(logout_url)
    else:
        webbrowser.open_new(logout_url)

    server = Server()
    server.start()
    while not terminate:
        time.sleep(1)
    server.shutdown()

    auth.IDENTITY_ID.set("")
    auth.ID_TOKEN.set("")
    auth.ACCESS_TOKEN.set("")
    auth.REFRESH_TOKEN.set("")
    auth.save()
