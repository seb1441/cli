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

import calendar
import enum
import json
import logging
from contextvars import ContextVar
from datetime import datetime
from os import environ

import boto3
import botocore
import botocore.config
import jwt
import requests
import requests.exceptions

from . import config


class State(enum.IntEnum):
    _ = enum.auto()
    INIT = enum.auto()
    GUEST = enum.auto()
    AUTH = enum.auto()


LOGGER = logging.getLogger(__name__)
AUTH_URL = environ.get("ICAUTH", "https://auth.ic.dev")
CREDS_PATH = config.HOME_PATH / "creds.json"
IDENTITY_ID: ContextVar[str] = ContextVar("identity_id")
ID_TOKEN: ContextVar[str] = ContextVar("id_token")
ACCESS_TOKEN: ContextVar[str] = ContextVar("access_token")
REFRESH_TOKEN: ContextVar[str] = ContextVar("refresh_token")
SESSION: ContextVar[boto3.Session] = ContextVar("session")
STATE: ContextVar[State] = ContextVar("state", default=State._)
REGION: str
USER_POOL_ID: str
ID_POOL_ID: str
CLIENT_ID: str


def init():
    # pylint: disable=bare-except,global-statement
    global REGION, USER_POOL_ID, ID_POOL_ID, CLIENT_ID
    if not CREDS_PATH.exists():
        data = config.REMOTE_CONFIG.get(None)
        if not data:
            return
        REGION = data["auth"]["region"]
        USER_POOL_ID = data["auth"]["user_pool_id"]
        ID_POOL_ID = data["auth"]["id_pool_id"]
        CLIENT_ID = data["auth"]["client_id"]
        save()
    data = json.loads(CREDS_PATH.read_text())
    REGION = data["region"]
    USER_POOL_ID = data["user_pool_id"]
    ID_POOL_ID = data["id_pool_id"]
    CLIENT_ID = data["client_id"]
    IDENTITY_ID.set(data.get("identity_id", ""))
    ID_TOKEN.set(data.get("id_token", ""))
    ACCESS_TOKEN.set(data.get("access_token", ""))
    REFRESH_TOKEN.set(data.get("refresh_token", ""))
    STATE.set(State.INIT)


def load():
    # pylint: disable=bare-except
    init()
    state = STATE.get()
    if state < State.INIT:
        return
    cognito = boto3.client(
        "cognito-identity",
        region_name=REGION,
        config=botocore.config.Config(
            signature_version=botocore.UNSIGNED,
            connect_timeout=1,
            read_timeout=1,
            retries={"max_attempts": 1},
        ),
    )
    if ACCESS_TOKEN.get():
        access_token = jwt.decode(ACCESS_TOKEN.get(), verify=False)
        now = calendar.timegm(datetime.utcnow().utctimetuple())
        if int(access_token["exp"]) <= now:
            token_url = f"{AUTH_URL}/oauth2/token"
            body = dict(
                grant_type="refresh_token",
                client_id=CLIENT_ID,
                refresh_token=REFRESH_TOKEN.get(),
            )
            try:
                with requests.post(token_url, data=body, timeout=1) as req:
                    req.raise_for_status()
                    res = req.json()
                    ID_TOKEN.set(res["id_token"])
                    ACCESS_TOKEN.set(res["access_token"])
                    state = State.AUTH
            except requests.exceptions.ConnectionError:
                return
            except:
                IDENTITY_ID.set("")
                ID_TOKEN.set("")
                ACCESS_TOKEN.set("")
                REFRESH_TOKEN.set("")
            save()
        else:
            state = State.AUTH
    if not IDENTITY_ID.get():
        try:
            new = cognito.get_id(IdentityPoolId=ID_POOL_ID)
        except:
            return
        IDENTITY_ID.set(new["IdentityId"])
        save()
    if state == state.INIT:
        state = State.GUEST
    try:
        logins = dict()
        if state == State.AUTH:
            provider = f"cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}"
            logins.update({provider: ID_TOKEN.get()})
        creds = cognito.get_credentials_for_identity(
            IdentityId=IDENTITY_ID.get(), Logins=logins
        )["Credentials"]
        sess = boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretKey"],
            aws_session_token=creds["SessionToken"],
            region_name=REGION,
        )
    except:
        return
    SESSION.set(sess)
    STATE.set(state)


def save():
    data = dict(
        version="v1",
        region=REGION,
        user_pool_id=USER_POOL_ID,
        id_pool_id=ID_POOL_ID,
        client_id=CLIENT_ID,
        identity_id=IDENTITY_ID.get(""),
        id_token=ID_TOKEN.get(""),
        access_token=ACCESS_TOKEN.get(""),
        refresh_token=REFRESH_TOKEN.get(""),
    )
    data = {k: v for k, v in data.items() if v}
    CREDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CREDS_PATH.write_text(json.dumps(data, indent=2, separators=(", ", ": ")))
    CREDS_PATH.chmod(0o600)
