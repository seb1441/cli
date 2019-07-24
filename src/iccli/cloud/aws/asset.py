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

import importlib.machinery
import importlib.resources
import pathlib

from . import types, util


class Asset:
    def __init__(
        self, package: str, name: str, path: pathlib.Path, info: util.AssetInfo
    ):
        self._package = package
        self._name = name
        self._info = info
        self._path = path

    def __hash__(self):
        return hash(self._path)

    def __eq__(self, other):
        return self._path == other

    def __str__(self):  # pragma: no cover
        return self._name

    @property
    def name(self) -> types.BridgeStr:
        return types.BridgeStr(self._name)

    @property
    def text(self) -> types.BridgeStr:
        return types.BridgeStr(importlib.resources.read_text(self._package, self._name))

    @property
    def url(self) -> types.BridgeStr:
        return self._info.url

    @property
    def uri(self) -> types.BridgeStr:
        return self._info.uri

    @property
    def bucket(self) -> types.BridgeStr:
        return self._info.bucket

    @property
    def key(self) -> types.BridgeStr:
        return self._info.key

    def __bool__(self) -> bool:
        return importlib.resources.is_resource(self._package, self.name)


class Assets:
    def __init__(self, package: str):
        self._package = package

    def __getitem__(self, item: str):
        from . import config

        with importlib.resources.path(self._package, item) as path:
            asset = Asset(self._package, item, path, util.asset_info(path))
            config.ASSETS.get().add(asset)
            return asset

    def __iter__(self):
        yield from (self[r] for r in importlib.resources.contents(self._package))
