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

import importlib
import importlib.resources
import pathlib
import sys
from typing import Optional

import pytest

from ...core import config as base_config
from ...core import importer as base_importer
from . import config, importer, testdata, types
from .resources import importer as rescs_importer


def setup_function(func):
    if "_import_icp_" in func.__name__:
        prefix, suffix, mode = "icpm", ".icp", base_config.Mode.ICP
    elif "_import_ic_" in func.__name__:
        prefix, suffix, mode = "icm", ".ic", base_config.Mode.IC
    else:
        raise NotImplementedError  # pragma: no cover

    def resolve(parent: Optional[pathlib.Path], name: str) -> Optional[pathlib.Path]:
        if name.endswith("dummy"):
            raise LookupError
        if parent is None:
            pkg = f"{testdata.__package__}.brick"
            with importlib.resources.path(pkg, suffix[1:]) as path:
                return path
        return parent.joinpath(name.rpartition(".")[-1])

    base_config.MODE.set(mode)
    config.REGION.set("us-east-1")
    config.SENSITIVES.set([])
    config.ASSETS.set(set())
    config.S3_BUCKET.set("test_bucket")
    config.S3_PREFIX.set("test_prefix/")
    finder = base_importer.Finder(prefix, suffix, "default", resolve, importer.Loader)
    sys.meta_path.insert(0, base_importer.LibFinder())
    sys.meta_path.insert(1, rescs_importer.Finder())
    sys.meta_path.insert(2, finder)

    if prefix == "icm":

        def resolve_index(
            parent: Optional[pathlib.Path], name: str
        ) -> Optional[pathlib.Path]:
            dots = name.count(".")
            pkg = f"{testdata.__package__}"
            with importlib.resources.path(pkg, "index") as path:
                root = path
            if parent is None and not dots:
                return root
            if dots == 0:
                # if requesting something from index with only the
                # username, then use namesapce packages
                return None
            if dots == 1:
                # now we have both username and component name and we
                # can proceed
                parts = name.split(".")
                return root / parts[0] / parts[1]
            assert parent
            return parent.joinpath(name.rpartition(".")[-1])

        finder = base_importer.Finder(
            "icx", suffix, "default", resolve_index, importer.Loader
        )
        sys.meta_path.insert(3, finder)


IMPORT_ICP_INVALID_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [
        ("scope", "icm", ModuleNotFoundError, None),
        ("resolve", "icpm.dummy", ModuleNotFoundError, None),
        ("exist", "icpm.smarap", ImportError, None),
        ("index", "icpm.index", ImportError, "expected ic"),
        ("relative", "icpm.relative", ImportError, "expected assets"),
        ("resource", "icpm.resource", ModuleNotFoundError, None),
    ],
)


@pytest.mark.parametrize("arg,err,match", IMPORT_ICP_INVALID_TESTS)
def test_import_icp_invalid(arg, err, match):
    with pytest.raises(err, match=match):
        importlib.import_module(arg)


IMPORT_ICP_VALID_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [
        ("default", "icpm.empty"),
        ("default_implicit", "icpm"),
        ("default_explicit", "icpm.default"),
        ("assets", "icpm.data"),
        ("lib", "icpm.lib"),
    ],
)


@pytest.mark.parametrize("arg", IMPORT_ICP_VALID_TESTS)
def test_import_icp_valid(arg):
    mod = importlib.import_module(arg)
    assert isinstance(mod, importer.Module)


def test_import_icp_assets():
    data = importlib.import_module("icpm.data")
    path = pathlib.Path(testdata.__file__).parent / "brick" / "icp"
    files = [f.name for f in path.iterdir() if f.is_file()]
    assert files == [a.name for a in data.data]
    assert all(a for a in data.data)
    assert data.text == (path / "data.icp").read_text()


def test_import_icp_lib():
    mod = importlib.import_module("icpm.lib")
    from ...lib import util

    assert callable(mod.sensitive)
    assert mod.sensitive.__name__ == util.sensitive.__name__


IMPORT_IC_INVALID_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [
        ("scope", "icpm", ModuleNotFoundError, None),
        ("resolve", "icm.dummy", ModuleNotFoundError, None),
        ("exist", "icm.xedni", ImportError, None),
    ],
)


@pytest.mark.parametrize("arg,err,match", IMPORT_IC_INVALID_TESTS)
def test_import_ic_invalid(arg, err, match):
    with pytest.raises(err, match=match):
        importlib.import_module(arg)


IMPORT_IC_VALID_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [
        ("default", "icm.empty"),
        ("default_implicit", "icm"),
        ("default_explicit", "icm.default"),
        ("assets", "icm.data"),
        ("lib", "icm.lib"),
        ("relative", "icm.relative"),
        ("index", "icm.index"),
        ("resource", "icm.resource"),
    ],
)


@pytest.mark.parametrize("arg", IMPORT_IC_VALID_TESTS)
def test_import_ic_valid(arg):
    mod = importlib.import_module(arg)
    assert isinstance(mod, importer.Module)


def test_import_ic_assets():
    # pylint: disable=line-too-long
    data = importlib.import_module("icm.data")
    path = pathlib.Path(testdata.__file__).parent / "brick" / "ic"
    files = [f.name for f in path.iterdir() if f.is_file()]
    assert files == [a.name for a in data.data]
    assert all(a for a in data.data)
    assert data.text == (path / "data.ic").read_text()
    assert (
        data.url
        == "https://test_bucket.s3.amazonaws.com/test_prefix/9914f6dbcf32f005343a4f32e11e45cfaee0c940"
    )
    assert (
        data.uri
        == "s3://test_bucket/test_prefix/9914f6dbcf32f005343a4f32e11e45cfaee0c940"
    )
    assert data.bucket == "test_bucket"
    assert data.key == "test_prefix/9914f6dbcf32f005343a4f32e11e45cfaee0c940"


def test_import_ic_lib():
    mod = importlib.import_module("icm.lib")
    from ...lib import awsutil

    assert callable(mod.b64encode)
    assert mod.b64encode.__name__ == awsutil.b64encode.__name__


def test_import_ic_relative():
    mod = importlib.import_module("icm.relative")
    assert mod.something.foo == "bar"


def test_import_ic_index():
    mod = importlib.import_module("icm.index")
    assert mod.org.com.bar == "baz"


def test_import_ic_resource():
    mod = importlib.import_module("icm.resource")
    from .resources import load

    spec = load("us-east-1")
    assert mod.ic.aws.iam.group == spec["aws"]["iam"]["group"]


IMPORT_IC_STR_VALID_TESTS = map(
    lambda t: pytest.param(*t[0:], id=t[0]),
    [
        ("simple", "- simple -"),
        ("fsimple", "- fsimple -"),
        ("ssimple", "- s- simple - -"),
        ("csimple", "- '- simple -' -"),
        ("cfsimple", "-   '- simple -' -"),
    ],
)


@pytest.mark.parametrize("name,expected", IMPORT_IC_STR_VALID_TESTS)
def test_import_ic_str_valid(name, expected):
    mod = importlib.import_module("icm.visit.str_valid")
    attr = getattr(mod, name)
    assert isinstance(attr, types.BridgeStr)
    assert attr == expected


def test_import_ic_str_opaque_valid():
    mod = importlib.import_module("icm.visit.str_valid")
    attr = mod.ocomplex
    assert isinstance(attr, types.Sub)
    assert attr.fmt == "-   '- simple -' ${A0} ${A1} -"
    assert "A0" in attr.args
    assert "A1" in attr.args


def test_import_ic_str_opaque_invalid():
    with pytest.raises(NotImplementedError, match="spec and conversion"):
        importlib.import_module("icm.visit.str_invalid")


def test_import_ic_def_valid():
    importlib.import_module("icm.visit.def_valid")


def test_import_ic_def_invalid():
    with pytest.raises(NotImplementedError, match="nested functions"):
        importlib.import_module("icm.visit.def_invalid")
