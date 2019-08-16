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
import sys

import click


class UserError(Exception):
    """Base class for exceptions that occur during normal operation of
    the CLI.

    Typically due to user error and can be resolved by the user.
    """

    ...


class LoggingStreamHandler(logging.StreamHandler):
    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover
        msg = super().format(record)
        if not sys.stderr.isatty():
            return msg
        color = ""
        if record.levelno >= logging.ERROR:
            color = "red"
        elif record.levelno == logging.WARNING:
            color = "yellow"
        return click.style(msg, fg=color)


def configure_logger(level: int):
    fmt = "%(message)s" if sys.stderr.isatty() else "%(levelname)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, handlers=[LoggingStreamHandler()])
