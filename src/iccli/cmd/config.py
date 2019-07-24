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

import configparser
import logging
from contextvars import ContextVar
from os import environ
from pathlib import Path

from . import util

HOME_PATH = Path(environ.get("ICHOME", Path.home() / ".ic")).resolve()
CACHE_PATH = HOME_PATH / "cache"
INDEX_PATH = HOME_PATH / "index"
CONFIG_PATH = HOME_PATH / "config.ini"
PROXY_URL = environ.get("ICPROXY", "https://api.ic.dev")
PROFILE: ContextVar[str] = ContextVar("profile")
CONFIG: ContextVar[configparser.ConfigParser] = ContextVar("config")
LOGGER = logging.getLogger(__name__)

if not HOME_PATH.exists():
    HOME_PATH.mkdir(parents=True, exist_ok=True)
if not CACHE_PATH.exists():
    CACHE_PATH.mkdir(parents=True, exist_ok=True)
if not INDEX_PATH.exists():
    INDEX_PATH.mkdir(parents=True, exist_ok=True)


def load(profile: str):
    """Load the config.ini file from ~/bricks directory."""
    config = configparser.ConfigParser(default_section="default")
    if CONFIG_PATH.exists():
        try:
            config.read(CONFIG_PATH)
        except configparser.Error as exc:
            LOGGER.error("%s:\n%s", str(CONFIG_PATH), str(exc))
            raise util.UserError("cannot parse config.ini")
    PROFILE.set(profile)
    CONFIG.set(config)


def save():
    """Save the updated config to the config.ini file."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w") as fpr:
        CONFIG.get().write(fpr)
