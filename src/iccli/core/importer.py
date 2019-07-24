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

import ast
import importlib.abc
import importlib.machinery
import importlib.util
import io
import pathlib
from functools import partial
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, Sequence, Type, Union

from . import config, resource


class LibFinder(importlib.abc.MetaPathFinder):
    @staticmethod
    def find_spec(
        name: str, path: Optional[Sequence[Union[bytes, str]]], target=None
    ) -> Optional[importlib.machinery.ModuleSpec]:
        # pylint: disable=unused-argument
        if name == "icl":
            return importlib.util.spec_from_loader(name, None, is_package=True)
        prefixes = tuple(f"icl.{x}" for x in {"util", "awsutil", "awsenv"})
        if name in prefixes:
            return importlib.util.find_spec(f"iccli.lib.{name.rpartition('.')[-1]}")
        return None


class Finder(importlib.abc.MetaPathFinder):
    def __init__(
        self,
        prefix: str,
        suffix: str,
        default: str,
        resolve: Callable[[Optional[pathlib.Path], str], Optional[pathlib.Path]],
        loader: Type["Loader"],
    ):
        self.prefix = prefix
        self.suffix = suffix
        self.default = default
        self.resolve = resolve
        self.loader = loader

    def find_spec(
        self, name: str, path: Optional[Sequence[Union[bytes, str]]], target=None
    ) -> Optional[importlib.machinery.ModuleSpec]:
        # pylint: disable=unused-argument
        prefix, _, real = name.partition(".")
        if prefix != self.prefix:
            return None
        try:
            origin = self.resolve(pathlib.Path(str(path[0])) if path else None, real)
        except LookupError:
            return None
        if not origin:
            return importlib.util.spec_from_loader(name, None, is_package=True)
        loader = self.loader()
        if origin.is_dir():
            index = origin.joinpath(self.default).with_suffix(self.suffix)
            spec = importlib.util.spec_from_loader(
                name, loader, origin=str(index), is_package=True
            )
            spec.has_location = index.is_file()
            spec.submodule_search_locations = [str(origin)]
        else:
            origin = origin.with_suffix(self.suffix)
            if not origin.is_file():
                par, _, curr = name.rpartition(".")
                org = f" ({pathlib.Path(str(path[0])) / 'index.ic'})" if path else ""
                raise ImportError(f"cannot import name {curr!r} from {par!r}{org}")
            spec = importlib.util.spec_from_loader(
                name, loader, origin=str(origin), is_package=False
            )
            spec.has_location = True
        spec.loader_state = None
        return spec


class Reader(importlib.abc.ResourceReader):
    # pylint: disable=arguments-differ

    def __init__(self, path: pathlib.Path):
        self.path = path

    def open_resource(self, resc):
        return io.BytesIO(self.resource_path(resc).read_bytes())

    def resource_path(self, resc):
        return self.path.joinpath(resc)

    def is_resource(self, name):
        return self.resource_path(name).exists()

    def contents(self):
        yield from (p.name for p in self.path.iterdir() if p.is_file())


class Loader(importlib.abc.Loader, ast.NodeTransformer):
    # pylint: disable=abstract-method

    @property
    def builtins(self) -> Dict[str, Any]:
        res = dict(
            __import__=import_module,
            enumerate=enumerate,
            isinstance=isinstance,
            partial=partial,
            print=print,
            Resource=resource.ResourceInfo,
        )
        if config.MODE.get() == config.Mode.IC:
            res.update(resource=resource.resource)
        return res

    def exec_module(self, module: ModuleType):
        assert module.__spec__
        if not module.__spec__.has_location:
            return
        src = pathlib.Path(module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source=src, filename=module.__file__)
        tree = ast.fix_missing_locations(self.visit(tree))
        code = compile(source=tree, filename=module.__file__, mode="exec")
        setattr(module, "__builtins__", self.builtins)
        exec(code, vars(module))  # pylint: disable=exec-used

    @staticmethod
    def get_resource_reader(name: str):
        module = importlib.import_module(name)
        assert module.__spec__
        assert module.__spec__.submodule_search_locations
        return Reader(pathlib.Path(module.__spec__.submodule_search_locations[0]))


def import_module(
    name: str,
    globals_: Dict[str, Any],
    locals_: Dict[str, Any],
    fromlist: List[str],
    level: int,
) -> Any:
    nsp = name.partition(".")[0]
    extra = None
    if level == 0:
        if nsp == "ic":
            name = f"icl{name[len('ic'):]}"
        elif config.MODE.get() == config.Mode.IC:
            name = f"icx.{name}"
            extra = nsp
        else:
            raise ImportError(f"invalid import {name!r}: expected ic.*")
    elif config.MODE.get() == config.Mode.ICP and fromlist != ("assets",):
        raise ImportError(f"invalid import {name!r}: expected assets")
    imp = __import__(name, globals_, locals_, fromlist, level)
    if extra and not fromlist:
        return getattr(imp, extra)
    return imp
