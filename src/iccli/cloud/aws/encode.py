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

import json
import re
from datetime import date, datetime
from typing import Any, Mapping, MutableMapping

from ...core.resource import Resource, ResourceInfo
from . import config, types
from .resources import Resource as AWSResource


class JSONEncoder(json.JSONEncoder):
    def default(self, node):
        # pylint: disable=too-many-return-statements,arguments-differ,method-hidden
        if isinstance(node, (date, datetime)):
            return node.isoformat()
        if isinstance(node, types.Sensitive):
            return {"Ref": node.name}
        if isinstance(node, types.Attr):
            return {"Fn::GetAtt": [node.rid, node.name]}
        if isinstance(node, types.Join):
            return {"Fn::Join": [node.delim, node.args]}
        if isinstance(node, types.Ref):
            return {"Ref": node.rid}
        if isinstance(node, types.Select):
            return {"Fn::Select": [node.item, node.args]}
        if isinstance(node, types.Split):
            return {"Fn::Split": [node.sep, node.arg]}
        if isinstance(node, types.Sub):
            return {"Fn::Sub": [node.fmt, node.args]}
        if isinstance(node, types.AvailabilityZones):
            return {"Fn::GetAZs": node.region}
        if isinstance(node, types.Base64Encode):
            return {"Fn::Base64": node.arg}
        if isinstance(node, types.CIDR):
            return {"Fn::Cidr": [node.block, node.count, node.bits]}
        if isinstance(node, types.AccountID):
            return {"Ref": "AWS::AccountId"}
        if isinstance(node, types.NotificationARNs):
            return {"Ref": "AWS::NotificationARNs"}
        if isinstance(node, types.Partition):
            return {"Ref": "AWS::Partition"}
        if isinstance(node, types.Region):
            return {"Ref": "AWS::Region"}
        if isinstance(node, types.StackID):
            return {"Ref": "AWS::StackId"}
        if isinstance(node, types.URLSuffix):
            return {"Ref": "AWS::URLSuffix"}
        return super().default(node)  # pragma: no cover


class Template:
    def __init__(self, node: Resource):
        self.node = node

    @property
    def tree(self) -> Mapping[str, Any]:
        return _tree(self.node)

    @staticmethod
    def _json_params(pretty=False):
        ind, sep = (2, (", ", ": ")) if pretty else (None, (",", ":"))
        return dict(indent=ind, separators=sep, sort_keys=False)

    @property
    def params(self):
        secs = config.SENSITIVES.get()
        return [dict(ParameterKey=s.name, ParameterValue=s.value) for s in secs]

    def dumps_params(self, pretty=False) -> str:
        return json.dumps(self.params, **self._json_params(pretty))

    def dumps_assets(self, pretty=False) -> str:
        # pylint: disable=protected-access
        assets = [
            dict(bucket=a.bucket, key=a.key, path=str(a._path), uri=a.uri, url=a.url)
            for a in config.ASSETS.get()
        ]
        return json.dumps(assets, **self._json_params(pretty))

    def dumps(self, pretty=False) -> str:
        # pylint: disable=protected-access
        meta = dict(resources=self.tree)
        desc = self.node.name
        tpl: MutableMapping[str, Any] = dict(
            AWSTemplateFormatVersion="2010-09-09", Description=desc, Metadata=meta
        )
        secs = config.SENSITIVES.get([])
        if secs:
            tpl.update(
                Parameters={s.name: dict(Type="String", NoEcho=True) for s in secs}
            )
        rescs: MutableMapping[str, Any] = {}
        for res in [r for r in self.node if isinstance(r, AWSResource)]:
            data: MutableMapping[str, Any] = dict(Type=res._type)
            if res._reqs:
                data.update(DependsOn=[r.id for r in res._reqs])
            if res._deletion:
                data.update(DeletionPolicy=res._deletion.title())
            if res.props:
                data.update(Properties=res._props)
            rescs[res.id] = data
        if not rescs:  # pragma: no cover
            raise TypeError("expected at least 1 AWS resource, got nothing")
        tpl.update(Resources=rescs)
        val = self.node if isinstance(self.node, AWSResource) else self.node._value
        if val is not None:
            subs: MutableMapping[str, types.Opaque] = {}
            out: Any = _strip(_output(val, subs))
            out = json.dumps(out, separators=(",", ":"), sort_keys=True)
            out = re.sub(r'(?:"##)(.+?)(?:##")', r"\1", out)
            if subs:
                out = types.Sub(out, subs)
            tpl.update(Outputs=dict(value=dict(Value=out)))
        tpl = _strip(tpl)
        return json.dumps(tpl, cls=JSONEncoder, **self._json_params(pretty))


def _strip(data: Any):
    none: Any = ("", None, {})
    if isinstance(data, dict):
        new_dict = {}
        for key, val in data.items():
            val = _strip(val)
            if not val in none:
                new_dict[key] = val
        return new_dict
    if isinstance(data, list):
        new_list = []
        for val in data:
            val = _strip(val)
            if not val in none:
                new_list.append(val)
        return new_list
    return data


def _tree(node: Resource) -> Mapping[str, Any]:
    res: MutableMapping[str, Any] = dict(id=node.id, name=node.name)
    if isinstance(node, AWSResource):
        res.update(type=node.type)
    if node.children:
        res.update(children=[_tree(c) for c in node.children])
    return res


def _output(node: Any, subs: MutableMapping[str, types.Opaque]):
    # pylint: disable=too-many-return-statements,protected-access
    if isinstance(node, ResourceInfo):
        node = node._items
    if isinstance(node, dict):
        return {k: _output(v, subs) for k, v in node.items() if not k.startswith("_")}
    if isinstance(node, list):
        return [_output(v, subs) for v in node]
    if isinstance(node, AWSResource):
        return {k: _output(v, subs) for k, v in node._attrs.items()}
    if not isinstance(node, types.Opaque):
        return node
    name = f"A{len(subs)}"
    if isinstance(node, types.List):
        if issubclass(node.select, types.Str):
            subs[name] = types.Join('","', node)
            return [f"${{{name}}}"]
    if isinstance(node, types.Str):
        subs[name] = node
        return f"${{{name}}}"
    if isinstance(node, (types.Bool, types.Int)):
        subs[name] = node
        return f"##${{{name}}}##"
    raise NotImplementedError(
        f"values of type {type(node).__name__!r} are not supported "
        f"in return values of AWS bricks"
    )  # pragma: no cover
