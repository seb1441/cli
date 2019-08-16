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

import base64
import hashlib
import importlib.resources
import logging
import secrets
import threading
import time
import urllib.parse
import webbrowser

import boto3
import botocore
import botocore.config
import click
import flask
import requests
import werkzeug.serving

from . import auth, util

LOGGER = logging.getLogger(__name__)


@click.command(name="login")
def cmd():
    """Log in to ic.dev"""
    auth.init()
    if auth.STATE.get() < auth.State.INIT:
        raise util.UserError("cannot init auth module")

    code_verifier = _encode(secrets.token_bytes(32))
    challenge = _encode(hashlib.sha256(code_verifier.encode("utf-8")).digest())
    state = _encode(secrets.token_bytes(32))
    redirect_uri = "http://localhost:21213/callback"

    params = dict(
        client_id=auth.CLIENT_ID,
        identity_provider="COGNITO",
        redirect_uri=redirect_uri,
        response_type="code",
        scope="openid",
        code_challenge_method="S256",
        code_challenge=challenge,
        state=state,
    )

    login_url = f"{auth.AUTH_URL}/login?{urllib.parse.urlencode(params)}"

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

    terminate, error, code, ctrl = False, None, None, None

    @app.route("/callback")
    def callback():  # pylint: disable=unused-variable
        nonlocal terminate, error, code, ctrl
        terminate = True
        if "error" in flask.request.args:
            error = flask.request.args["error"]
            if "error_description" in flask.request.args:
                error += f": {flask.request.args['error_description']}"
        else:
            code = flask.request.args["code"]
        ctrl = flask.request.args["state"]
        return importlib.resources.read_text(__package__, "callback.html")

    click.echo("If nothing happens, copy and paste this URL into your browser:\n")
    click.echo(login_url)
    click.echo()
    webbrowser.open_new(login_url)

    server = Server()
    server.start()
    try:
        while not terminate:
            time.sleep(1)
    except KeyboardInterrupt:
        server.shutdown()
        raise
    server.shutdown()
    if state != ctrl:
        raise util.UserError(
            "Session replay attack in progress. Please log out of all connections."
        )
    if error:
        raise util.UserError(error)

    token_url = f"{auth.AUTH_URL}/oauth2/token"
    body = dict(
        grant_type="authorization_code",
        client_id=auth.CLIENT_ID,
        code_verifier=code_verifier,
        code=code,
        redirect_uri=redirect_uri,
    )
    with requests.post(token_url, data=body) as req:
        req.raise_for_status()
        res = req.json()
        auth.ID_TOKEN.set(res["id_token"])
        auth.ACCESS_TOKEN.set(res["access_token"])
        auth.REFRESH_TOKEN.set(res["refresh_token"])

    cognito = boto3.client(
        "cognito-identity",
        region_name=auth.REGION,
        config=botocore.config.Config(signature_version=botocore.UNSIGNED),
    )
    provider = f"cognito-idp.{auth.REGION}.amazonaws.com/{auth.USER_POOL_ID}"
    logins = {provider: auth.ID_TOKEN.get()}
    identity_id = auth.IDENTITY_ID.get()
    if identity_id:
        try:
            new = cognito.get_open_id_token(IdentityId=identity_id, Logins=logins)
        except cognito.exceptions.NotAuthorizedException as exc:
            res = exc.response["Error"]
            code, msg = res["Code"], res["Message"]
            if code == "NotAuthorizedException" and "Logins don't match." in msg:
                identity_id = ""
            else:
                raise
        else:
            auth.IDENTITY_ID.set(new["IdentityId"])
    if not identity_id:
        new = cognito.get_id(IdentityPoolId=auth.ID_POOL_ID, Logins=logins)
        auth.IDENTITY_ID.set(new["IdentityId"])
    auth.save()


def _encode(val: bytes) -> str:
    return base64.urlsafe_b64encode(val).decode("utf-8").rstrip("=")
