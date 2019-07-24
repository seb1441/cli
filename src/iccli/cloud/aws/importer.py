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
import importlib.machinery
import importlib.resources
from collections import defaultdict
from types import ModuleType
from typing import Any, Dict

from ...core import importer
from . import asset, types


class Module(ModuleType):
    # pylint: disable=too-few-public-methods
    __package__: str

    @property
    def assets(self):
        return asset.Assets(self.__package__)


class Loader(importer.Loader):
    # pylint: disable=abstract-method,invalid-name

    def __init__(self):
        super().__init__()
        self.in_def = False

    @property
    def builtins(self) -> Dict[str, Any]:
        res = super().builtins
        res.update(
            opaque=types.Opaque,
            str=types.BridgeStr,
            _fstr=types.fstr,
            _fval=types.fval,
            bool=bool,
            float=float,
            dict=dict,
            defaultdict=defaultdict,
            int=int,
            list=list,
            set=set,
            tuple=tuple,
        )
        return res

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> ModuleType:
        return Module(spec.name)

    def visit_FormattedValue(self, node):
        self.generic_visit(node)
        return ast.Call(
            func=ast.Name(id="_fval", ctx=ast.Load()),
            args=[
                node.value,
                ast.Num(n=node.conversion),
                node.format_spec or ast.NameConstant(value=None),
            ],
            keywords=[],
        )

    def visit_JoinedStr(self, node):
        self.generic_visit(node)
        return ast.Call(
            func=ast.Name(id="_fstr", ctx=ast.Load()),
            args=[ast.List(elts=node.values, ctx=ast.Load())],
            keywords=[],
        )

    @staticmethod
    def visit_Str(node):
        return ast.Call(
            func=ast.Name(id="str", ctx=ast.Load()), args=[node], keywords=[]
        )

    def visit_FunctionDef(self, node):
        if self.in_def:
            raise NotImplementedError("nested functions are not supported")
        self.in_def = True
        self.generic_visit(node)
        self.in_def = False
        return node
