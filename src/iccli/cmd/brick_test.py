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

import pytest

from . import brick, util

CHECK_NAME_INVALID_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [
        ("empty", ""),
        ("type", 1),
        ("relative", ".org.com"),
        ("case", "oRg.com"),
        ("char", "o-g.com"),
        ("format", "o.r.g.c.o.m"),
        ("digit", "1org.1com"),
        ("python", "continue.for"),
        ("reserved", "icp.brick"),
        ("min", "xy.z"),
        ("max", f"{'x'*21}.{'y'*21}"),
    ],
)


@pytest.mark.parametrize("val", CHECK_NAME_INVALID_TESTS)
def test_check_name_invalid(val):
    with pytest.raises(util.UserError):
        brick.check_name(val)


CHECK_NAME_VALID_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [("simple", "org.com"), ("complex", "complex_org1.complex_comv2")],
)


@pytest.mark.parametrize("val", CHECK_NAME_VALID_TESTS)
def test_check_name_valid(val):
    brick.check_name(val)


CHECK_VERSION_INVALID_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [
        ("empty", ""),
        ("type", 1),
        ("prefix", "1.2.3"),
        ("patch", "v1.2"),
        ("minor", "v1"),
        ("build", "v1.2.3+build"),
    ],
)


@pytest.mark.parametrize("val", CHECK_VERSION_INVALID_TESTS)
def test_check_version_invalid(val):
    with pytest.raises(util.UserError):
        brick.check_version(val)


CHECK_VERSION_VALID_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [("simple", "v1.2.3"), ("pre", "v1.2.3-pre")],
)


@pytest.mark.parametrize("val", CHECK_VERSION_VALID_TESTS)
def test_check_version_valid(val):
    brick.check_version(val)


CHECK_ID_INVALID_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [
        ("mismatch_1", "org.com", "v2.0.0"),
        ("mismatch_2", "org.comv2", "v1.0.0"),
        ("endwith_v", "org.comv", "v1.0.0"),
        ("endwith_digit", "org.com1", "v1.0.0"),
    ],
)


@pytest.mark.parametrize("name,version", CHECK_ID_INVALID_TESTS)
def test_check_id_invalid(name, version, mocker):
    mocker.patch("iccli.cmd.brick.check_name")
    mocker.patch("iccli.cmd.brick.check_version")
    with pytest.raises(util.UserError):
        brick.check_id(name, version)


CHECK_ID_VALID_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [
        ("v0", "org.com", "v0.1.0"),
        ("v1", "org.com", "v1.0.0"),
        ("v2", "org.comv2", "v2.0.0"),
    ],
)


@pytest.mark.parametrize("name,version", CHECK_ID_VALID_TESTS)
def test_check_id_valid(name, version, mocker):
    mocker.patch("iccli.cmd.brick.check_name")
    mocker.patch("iccli.cmd.brick.check_version")
    brick.check_id(name, version)


CHECK_PRIVATE_INVALID_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]), [("type", 1)]
)


@pytest.mark.parametrize("val", CHECK_PRIVATE_INVALID_TESTS)
def test_check_private_invalid(val):
    with pytest.raises(util.UserError):
        brick.check_private(val)


CHECK_LICENSE_INVALID_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [
        ("type_private", 1, True),
        ("type_public", 1, False),
        ("empty", "", False),
        ("spdx", "DUMMY", False),
    ],
)


@pytest.mark.parametrize("val,private", CHECK_LICENSE_INVALID_TESTS)
def test_check_license_invalid(val, private):
    with pytest.raises(util.UserError):
        brick.check_license(val, private)


CHECK_LICENSE_VALID_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [
        ("private", "ANYTHING", True),
        ("public_1", "MIT", False),
        ("public_2", "Apache-2.0", False),
    ],
)


@pytest.mark.parametrize("val,private", CHECK_LICENSE_VALID_TESTS)
def test_check_license_valid(val, private):
    brick.check_license(val, private)


CHECK_DESCRIPTION_INVALID_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]), [("type", 1), ("length", "x" * 141)]
)


@pytest.mark.parametrize("val", CHECK_DESCRIPTION_INVALID_TESTS)
def test_description_main_invalid(val):
    with pytest.raises(util.UserError):
        brick.check_description(val)


CHECK_DESCRIPTION_VALID_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]), [("simple", "x" * 140)]
)


@pytest.mark.parametrize("val", CHECK_DESCRIPTION_VALID_TESTS)
def test_check_description_valid(val):
    brick.check_description(val)


CHECK_MAIN_INVALID_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [("empty", ""), ("type", 1), ("absolute", "foo.bar:brick"), ("format", ".foo.bar")],
)


@pytest.mark.parametrize("val", CHECK_MAIN_INVALID_TESTS)
def test_check_main_invalid(val):
    with pytest.raises(util.UserError):
        brick.check_main(val)


CHECK_MAIN_VALID_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [("complete", ".foo.bar:brick"), ("shortcut", ":brick")],
)


@pytest.mark.parametrize("val", CHECK_MAIN_VALID_TESTS)
def test_check_main_valid(val):
    brick.check_main(val)
