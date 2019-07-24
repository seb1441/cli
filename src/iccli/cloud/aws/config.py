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

from contextvars import ContextVar
from typing import List, Set

import boto3

from . import types

# SENSITIVES and ASSETS must be reset before each build.

SENSITIVES: ContextVar[List[types.Sensitive]] = ContextVar("sensitives")
PROFILE: ContextVar[str] = ContextVar("profile")
REGION: ContextVar[str] = ContextVar("region")
SESSION: ContextVar[boto3.Session] = ContextVar("session")
S3_BUCKET: ContextVar[str] = ContextVar("s3_bucket")
S3_PREFIX: ContextVar[str] = ContextVar("s3_prefix")
ASSETS: ContextVar[Set] = ContextVar("assets")
