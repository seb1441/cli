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
from datetime import date, datetime

import pytest

from ...core import resource
from . import config, encode, resources, types

JSON_ENCODER_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [
        ("date", date(2013, 2, 21), "2013-02-21"),
        ("datetime", datetime(2013, 2, 21, 14, 21, 13), "2013-02-21T14:21:13"),
        ("sensitive", types.Sensitive("param", "secret"), {"Ref": "param"}),
        (
            "Fn::GetAtt",
            types.Attr[types.Str, "attr"]("resc"),  # type: ignore
            {"Fn::GetAtt": ["resc", "attr"]},
        ),
        (
            "Fn::Join",
            types.Join("-", types.NotificationARNs()),
            {"Fn::Join": ["-", {"Ref": "AWS::NotificationARNs"}]},
        ),
        ("Ref", types.Ref("resc"), {"Ref": "resc"}),
        (
            "Fn::Select",
            types.Select[types.Str](1, types.AvailabilityZones()),  # type: ignore
            {"Fn::Select": [1, {"Fn::GetAZs": {"Ref": "AWS::Region"}}]},
        ),
        (
            "Fn::Split",
            types.Split("-", types.URLSuffix()),
            {"Fn::Split": ["-", {"Ref": "AWS::URLSuffix"}]},
        ),
        (
            "Fn::Sub",
            types.Sub(
                "- ${A0} ${A1} -", {"A0": types.AccountID(), "A1": types.StackID()}
            ),
            {
                "Fn::Sub": [
                    "- ${A0} ${A1} -",
                    {"A0": {"Ref": "AWS::AccountId"}, "A1": {"Ref": "AWS::StackId"}},
                ]
            },
        ),
        (
            "Fn::Base64",
            types.Base64Encode(types.Partition()),
            {"Fn::Base64": {"Ref": "AWS::Partition"}},
        ),
        (
            "Fn::Cidr",
            types.CIDR(types.Ref("resc"), 6, 5),
            {"Fn::Cidr": [{"Ref": "resc"}, 6, 5]},
        ),
    ],
)


@pytest.mark.parametrize("arg,expected", JSON_ENCODER_TESTS)
def test_json_encoder(arg, expected):
    assert json.dumps(arg, cls=encode.JSONEncoder) == json.dumps(expected)


TEMPLATE1 = json.dumps(
    # pylint: disable=line-too-long
    {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "root",
        "Metadata": {
            "resources": {
                "id": "3r3ot4ga",
                "name": "root",
                "children": [
                    {
                        "id": "ulpcqofl",
                        "name": "wch",
                        "type": "aws.cloudformation.wait_condition_handle",
                    },
                    {
                        "id": "ikiqhwco",
                        "name": "car",
                        "type": "aws.ec2.capacity_reservation",
                    },
                ],
            }
        },
        "Parameters": {"param": {"Type": "String", "NoEcho": True}},
        "Resources": {
            "ulpcqofl": {
                "Type": "AWS::CloudFormation::WaitConditionHandle",
                "DeletionPolicy": "Retain",
            },
            "ikiqhwco": {
                "Type": "AWS::EC2::CapacityReservation",
                "DependsOn": ["ulpcqofl"],
                "Properties": {
                    "AvailabilityZone": "az",
                    "InstancePlatform": "pl",
                    "InstanceCount": 1,
                    "InstanceType": "it",
                },
            },
        },
        "Outputs": {
            "value": {
                "Value": {
                    "Fn::Sub": [
                        '{"data":[{"ref":"${A0}"},{"availability_zone":"${A3}","available_instance_count":${A2},"instance_type":"${A5}","ref":"${A6}","tenancy":"${A1}","total_instance_count":${A4}}],"list":["${A7}"],"why":42}',
                        {
                            "A0": {"Ref": "ulpcqofl"},
                            "A1": {"Fn::GetAtt": ["ikiqhwco", "Tenancy"]},
                            "A2": {
                                "Fn::GetAtt": ["ikiqhwco", "AvailableInstanceCount"]
                            },
                            "A3": {"Fn::GetAtt": ["ikiqhwco", "AvailabilityZone"]},
                            "A4": {"Fn::GetAtt": ["ikiqhwco", "TotalInstanceCount"]},
                            "A5": {"Fn::GetAtt": ["ikiqhwco", "InstanceType"]},
                            "A6": {"Ref": "ikiqhwco"},
                            "A7": {
                                "Fn::Join": [
                                    '","',
                                    {"Fn::Split": ["-", {"Ref": "AWS::Region"}]},
                                ]
                            },
                        },
                    ]
                }
            }
        },
    },
    separators=(",", ":"),
    sort_keys=False,
)

TEMPLATE2 = json.dumps(
    {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "wch",
        "Metadata": {
            "resources": {
                "id": "u6pzt3h2",
                "name": "wch",
                "type": "aws.cloudformation.wait_condition_handle",
            }
        },
        "Resources": {"u6pzt3h2": {"Type": "AWS::CloudFormation::WaitConditionHandle"}},
        "Outputs": {
            "value": {
                "Value": {"Fn::Sub": ['{"ref":"${A0}"}', {"A0": {"Ref": "u6pzt3h2"}}]}
            }
        },
    },
    separators=(",", ":"),
    sort_keys=False,
)

TEMPLATE3 = json.dumps(
    {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "root",
        "Metadata": {
            "resources": {
                "id": "3r3ot4ga",
                "name": "root",
                "children": [
                    {
                        "id": "njbmlqra",
                        "name": "par",
                        "type": "aws.cloudformation.wait_condition_handle",
                    },
                    {
                        "id": "7lok7666",
                        "name": "inner",
                        "children": [
                            {
                                "id": "nf2f6dlm",
                                "name": "sub",
                                "type": "aws.cloudformation.wait_condition_handle",
                            },
                            {
                                "id": "7ecxyrnv",
                                "name": "sub_later_foo_baz",
                                "type": "aws.cloudformation.wait_condition_handle",
                            },
                            {
                                "id": "elaovd67",
                                "name": "sub_coord_qux",
                                "type": "aws.cloudformation.wait_condition_handle",
                            },
                        ],
                    },
                ],
            }
        },
        "Resources": {
            "njbmlqra": {"Type": "AWS::CloudFormation::WaitConditionHandle"},
            "nf2f6dlm": {"Type": "AWS::CloudFormation::WaitConditionHandle"},
            "7ecxyrnv": {"Type": "AWS::CloudFormation::WaitConditionHandle"},
            "elaovd67": {"Type": "AWS::CloudFormation::WaitConditionHandle"},
        },
        "Outputs": {
            "value": {
                "Value": {
                    "Fn::Sub": [
                        '{"baz":"qux","wch":{"ref":"${A0}"}}',
                        {"A0": {"Ref": "nf2f6dlm"}},
                    ]
                }
            }
        },
    },
    separators=(",", ":"),
    sort_keys=False,
)


def test_template():
    # pylint: disable=protected-access
    spec = resources.load("us-east-1")

    @resource.resource
    def brick():
        wch = spec["aws"]["cloudformation"]["wait_condition_handle"]("wch")
        wch.deletion = "retain"
        car = spec["aws"]["ec2"]["capacity_reservation"](
            "car",
            availability_zone="az",
            instance_platform="pl",
            instance_count=1,
            instance_type="it",
            tenancy=None,
        )
        car.require(wch)
        return dict(
            data=[wch, car],
            why=42,
            list=types.Region().split("-"),
            _private="private",
            none=None,
        )

    config.SENSITIVES.set([types.Sensitive("param", "secret")])
    node = brick("root")
    tpl = encode.Template(node)
    assert TEMPLATE1 == tpl.dumps()
    assert tpl.dumps_params() == '[{"ParameterKey":"param","ParameterValue":"secret"}]'

    config.SENSITIVES.set([])
    node = spec["aws"]["cloudformation"]["wait_condition_handle"]("wch")
    tpl = encode.Template(node)
    assert TEMPLATE2 == tpl.dumps()
    assert tpl.dumps_params() == "[]"


def test_info():
    # pylint: disable=expression-not-assigned,unused-variable
    spec = resources.load("us-east-1")

    @resource.resource
    def brick():
        spec["aws"]["cloudformation"]["wait_condition_handle"]("par"),
        sub = sub_brick("inner")
        sub.later("foo", bar="baz")
        return sub

    @resource.resource
    def sub_brick():
        return resource.ResourceInfo(
            wch=spec["aws"]["cloudformation"]["wait_condition_handle"]("sub"),
            later=later,
            coord=coord,
            baz="qux",
        )

    def later(self, foo, *, bar):
        spec["aws"]["cloudformation"]["wait_condition_handle"](f"sub_later_{foo}_{bar}")
        self.coord()

    def coord(self):
        spec["aws"]["cloudformation"]["wait_condition_handle"](
            f"sub_coord_{self['baz']}"
        )

    node = brick("root")
    tpl = encode.Template(node)
    assert TEMPLATE3 == tpl.dumps()
