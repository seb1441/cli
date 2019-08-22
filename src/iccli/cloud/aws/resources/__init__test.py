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

from datetime import datetime, timezone
from functools import partial

import pytest

from .. import types
from . import (
    ObjectChecker,
    _check_any,
    _check_list,
    _check_map,
    _check_number,
    _check_timestamp,
    _check_type,
    load,
)

REGIONS_TESTS = map(
    lambda t: pytest.param(t, id=t),
    [
        "ap-northeast-1",
        "ap-northeast-2",
        "ap-northeast-3",
        "ap-south-1",
        "ap-southeast-1",
        "ap-southeast-2",
        "ca-central-1",
        "eu-central-1",
        "eu-north-1",
        "eu-west-1",
        "eu-west-2",
        "eu-west-3",
        "sa-east-1",
        "us-east-1",
        "us-east-2",
        "us-west-1",
        "us-west-2",
    ],
)


@pytest.mark.parametrize("val", REGIONS_TESTS)
def test_load(val: str):
    spec = load(val)
    func = spec["aws"]["lambda_"]["function"]

    with pytest.raises(TypeError, match="missing required keys"):
        func("dummy")

    with pytest.raises(TypeError, match="got unexpected keys"):
        func("dummy", foo=42)

    with pytest.raises(TypeError, match="incompatible type"):
        func("dummy", role="", runtime="", handler="", code=42)

    # int <-> str
    func("func", role="", runtime="", handler="", code={}, memory_size="128")

    bucket = spec["aws"]["s3"]["bucket"]

    with pytest.raises(TypeError, match="missing timezone"):
        # must have timezone like `datetime.now(timezone.utc)`
        bucket(
            "dummy",
            lifecycle_configuration=dict(
                rules=[dict(status="Enabled", expiration_date=datetime.utcnow())]
            ),
        )

    cluster = spec["aws"]["emr"]["cluster"]

    with pytest.raises(TypeError, match="x: incompatible type 'int'"):
        cluster(
            "dummy",
            instances={},
            name="",
            service_role="",
            job_flow_role="",
            configurations=[dict(configuration_properties=dict(x=1))],
        )

    wch = spec["aws"]["cloudformation"]["wait_condition_handle"]("wch")

    assert isinstance(wch["ref"], types.Ref)
    assert wch.type == "aws.cloudformation.wait_condition_handle"
    assert wch.id == "u6pzt3h2"

    wch.props = {}
    wch.props["foo"] = "bar"  # type: ignore
    assert wch.props == {}

    with pytest.raises(TypeError, match="got unexpected keys: {'foo'}"):
        wch.props = {"foo": "bar"}

    # pylint: disable=protected-access

    with pytest.raises(ValueError, match="invalid deletion policy"):
        wch.deletion = "dummy"  # type: ignore

    wch.deletion = "retain"  # type: ignore
    assert wch._deletion == "retain"

    wch.require(wch)
    assert wch in wch._reqs


CHECK_NONE_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [
        ("any", _check_any),
        ("type", partial(_check_type, (set,))),
        ("number", _check_number),
        ("timestamp", _check_timestamp),
        ("list", partial(_check_list, _check_any)),
        ("map", partial(_check_map, _check_any)),
    ],
)


@pytest.mark.parametrize("func", CHECK_NONE_TESTS)
def test_check_none(func):
    func(None)


CHECK_VAL_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [
        ("any", _check_any, set()),
        ("type", partial(_check_type, (set,)), set()),
        ("number", _check_number, 42),
        ("timestamp", _check_timestamp, datetime.now(timezone.utc)),
        ("list", partial(_check_list, _check_any), [42]),
        ("list", partial(_check_list, _check_any), types.List()),
        ("map", partial(_check_map, _check_any), {"foo": "bar"}),
    ],
)


@pytest.mark.parametrize("func,val", CHECK_VAL_TESTS)
def test_check_val(func, val):
    assert val == func(val)


def test_check_object_none():
    check = ObjectChecker()
    check.reqs = set()
    check.items = dict()
    check(None)


def test_none():
    spec = load("us-east-1")

    func = spec["aws"]["lambda_"]["function"]

    with pytest.raises(TypeError, match="missing required keys"):
        func("dummy")

    with pytest.raises(TypeError, match="missing required keys"):
        func("dummy", role=None, runtime="", handler="", code=dict())

    with pytest.raises(TypeError, match="got unexpected keys"):
        func("dummy", foo=None)

    func("dummy", role="", runtime="", handler="", code=dict(zip_file=None))

    bucket = spec["aws"]["s3"]["bucket"]

    bucket("dummy", lifecycle_configuration=None)
    bucket(
        "dummy",
        lifecycle_configuration=dict(
            rules=[dict(status="Enabled", expiration_date=None), None]
        ),
    )
    bucket(
        "dummy",
        lifecycle_configuration=dict(rules=[dict(status="Enabled", tag_filters=None)]),
    )

    cluster = spec["aws"]["emr"]["cluster"]

    cluster(
        "dummy",
        instances={},
        name="",
        service_role="",
        job_flow_role="",
        configurations=[dict(configuration_properties=dict(x=None, y="y"))],
    )


def test_custom():
    spec = load("us-east-1")

    resc = spec["aws"]["cloudformation"]["custom_resource"]

    with pytest.raises(TypeError, match="missing required keys"):
        resc("custom")

    with pytest.raises(TypeError, match="got malformed key"):
        resc("custom", service_token="dummy", Mixed_Case=42)

    resc("custom", service_token="dummy", custom_prop_1=42, custom_prop_2="Foo")


def test_erasure(caplog):
    from ....core import resource

    spec = load("us-east-1")
    bucket = spec["aws"]["s3"]["bucket"]

    @resource.resource
    def root():
        bucket("same")
        bucket("same")

    root("root")

    assert "'root.same.aws.s3.bucket' node has been erased" in caplog.text
