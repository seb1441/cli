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
import pathlib
from functools import lru_cache, partial
from typing import IO, NamedTuple, Union

from . import config, types


@lru_cache()
def stack_name(resource: str) -> str:
    hash_ = hashlib.sha1(resource.encode("utf-8"))
    name = base64.b32encode(hash_.digest()[:5]).lower().decode("utf-8")
    return f"ic-{name}"


class AssetInfo(NamedTuple):
    url: types.BridgeStr
    uri: types.BridgeStr
    bucket: types.BridgeStr
    key: types.BridgeStr


def asset_info(data: Union[pathlib.Path, IO[bytes]]) -> AssetInfo:
    hasher = hashlib.sha1()

    def _hash(reader):
        for block in iter(partial(reader.read, 65536), b""):
            hasher.update(block)

    if isinstance(data, pathlib.Path):
        with data.open("rb") as ptr:
            _hash(ptr)
    else:  # pragma: no cover
        # only when template > 52K
        _hash(data)
    buk = config.S3_BUCKET.get()
    key = f"{config.S3_PREFIX.get()}{hasher.hexdigest()}"
    return AssetInfo(
        url=types.BridgeStr(f"https://{buk}.s3.amazonaws.com/{key}"),
        uri=types.BridgeStr(f"s3://{buk}/{key}"),
        bucket=types.BridgeStr(buk),
        key=types.BridgeStr(key),
    )
