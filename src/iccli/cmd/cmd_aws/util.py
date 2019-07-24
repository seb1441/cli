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
from contextlib import suppress
from typing import IO, Iterable, Optional, Tuple, Union

import boto3
import botocore.exceptions
import botocore.session

from ...cloud.aws import config
from ...cloud.aws import util as aws_util
from .. import brick
from .. import config as cli_config
from .. import util

LOGGER = logging.getLogger(__name__)


def init_session(profile: Optional[str], region: Optional[str]):
    try:
        _sess = botocore.session.Session(profile=profile)
        creds = _sess.get_component("credential_provider")
        role = creds.get_provider("assume-role")
        role.cache = botocore.credentials.JSONFileCache(
            str(pathlib.Path.home() / ".aws" / "cli" / "cache")
        )
        sess = boto3.Session(botocore_session=_sess, region_name=region)
    except Exception as exc:
        raise util.UserError(f"aws: {exc}")
    if not sess.region_name:
        raise util.UserError("missing aws region")
    config.PROFILE.set(sess.profile_name)
    config.REGION.set(sess.region_name)
    config.SESSION.set(sess)


def upload(
    artifacts: Iterable[Tuple[Union[pathlib.Path, IO[bytes]], aws_util.AssetInfo]]
):
    if not artifacts:
        return
    if config.S3_BUCKET.get() == "<not provided>":
        raise util.UserError("missing aws s3 bucket")

    client = config.SESSION.get().client("s3")
    dest_logged = False

    def log_op(loc, key):
        nonlocal dest_logged
        if not dest_logged:
            LOGGER.info("bucket s3://%s", config.S3_BUCKET.get())
            dest_logged = True
        LOGGER.info("upload %s -> %s", loc, key)

    for data, info in artifacts:
        with suppress(botocore.exceptions.ClientError):
            client.head_object(Bucket=info.bucket, Key=info.key)
            continue
        if isinstance(data, pathlib.Path):
            root = brick.ROOT.get(pathlib.Path.cwd())
            if cli_config.INDEX_PATH in data.parents:
                loc = f"index:{str(data.relative_to(cli_config.INDEX_PATH))}"
            else:
                loc = f"brick:{str(data.relative_to(root))}"
            log_op(loc, info.key)
            client.upload_file(str(data), info.bucket, info.key)
        else:  # pragma: no cover
            # only when template > 52K
            loc = "brick:<generated template>"
            log_op(loc, info.key)
            client.upload_fileobj(data, info.bucket, info.key)
