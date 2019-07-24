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

import importlib.abc
import importlib.machinery
import importlib.util
from typing import Optional, Sequence, Union

from ....core import config as base_config
from .. import config
from . import load


class Finder(importlib.abc.MetaPathFinder):
    @staticmethod
    def find_spec(
        name: str, path: Optional[Sequence[Union[bytes, str]]], target=None
    ) -> Optional[importlib.machinery.ModuleSpec]:
        # pylint: disable=unused-argument
        if base_config.MODE.get() == base_config.Mode.ICP:
            return None
        if name == "icl":
            return importlib.util.spec_from_loader(name, None, is_package=True)
        spec = load(config.REGION.get())
        prefixes = tuple(f"icl.{x}" for x in spec)
        if name in prefixes:
            vnd = spec[name.rpartition(".")[-1]]
            return importlib.util.spec_from_loader(name, Loader(vnd), is_package=True)
        for prefix in prefixes:
            if name.startswith(prefix):
                svcs = spec[prefix.rpartition(".")[-1]]
                postfix = name[len(f"{prefix}.") :]
                break
        else:
            return None
        parts = postfix.split(".")
        if len(parts) == 1 and parts[0] in svcs:
            svc = svcs[parts[0]]
            return importlib.util.spec_from_loader(name, Loader(svc), is_package=False)
        return None


class Loader(importlib.abc.Loader):
    # pylint: disable=abstract-method

    def __init__(self, exports):
        self.exports = exports

    def create_module(self, spec):
        ...

    def exec_module(self, module):
        vars(module)["__all__"] = list(self.exports.keys())
        if not hasattr(module, "__path__"):
            vars(module).update(self.exports)
        else:
            for key in self.exports:
                importlib.import_module(f"{module.__name__}.{key}")
