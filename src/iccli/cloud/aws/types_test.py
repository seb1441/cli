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

from . import types


def test_opaque_truth():
    with pytest.raises(TypeError):
        if types.Bool():
            ...  # pragma: no cover


def test_str_split():
    val = types.Str()
    got = val.split("-")

    assert isinstance(got, types.Split)
    assert (got.sep, got.arg) == ("-", val)


def test_str_replace():
    val = types.Str()
    with pytest.raises(NotImplementedError):
        val.replace("-", "+", 42)
    got = val.replace("-", "+")

    assert isinstance(got, types.Join)
    assert got.delim == "+"
    assert isinstance(got.args, types.Split)
    assert (got.args.sep, got.args.arg) == ("-", val)


def test_str_add():
    str1 = types.Str()
    str2 = types.Str()
    with pytest.raises(TypeError):
        print(str1 + 42)
    got = str1 + str2

    assert isinstance(got, types.Join)
    assert got.delim == ""
    assert got.args == [str1, str2]


def test_list():
    val = types.List[types.Str]()  # type: ignore
    with pytest.raises(TypeError):
        print(val["dummy"])
    got = val[1]

    assert isinstance(got, types.Select)
    assert (got.item, got.args) == (1, val)


def test_sensitive():
    with pytest.raises(TypeError):
        types.Sensitive("dummy", 1)


BRIDGE_STR_STR_TESTS = map(
    lambda t: pytest.param(*t[0:], id=t[0]),
    [
        ("__getitem__", "bar", (1,), "a"),
        ("__add__", types.BridgeStr("a"), (types.BridgeStr("b"),), "ab"),
        ("__mul__", "a", (3,), "aaa"),
        ("__rmul__", "a", (3,), "aaa"),
        ("capitalize", "abc", (), "Abc"),
        ("casefold", "ß", (), "ss"),
        ("center", "a", (3,), " a "),
        ("expandtabs", "\ta", (2,), "  a"),
        ("join", ".", ([types.BridgeStr("a"), types.BridgeStr("b")],), "a.b"),
        ("ljust", "a", (3,), "a  "),
        ("lower", "ABC", (), "abc"),
        ("lstrip", "  a", (), "a"),
        ("replace", "aca", (types.BridgeStr("a"), types.BridgeStr("b")), "bcb"),
        ("rjust", "a", (3,), "  a"),
        ("rstrip", "a  ", (), "a"),
        ("strip", "  a  ", (), "a"),
        ("swapcase", "aBc", (), "AbC"),
        ("title", "abc def", (), "Abc Def"),
        ("upper", "abc", (), "ABC"),
        ("zfill", "a", (3,), "00a"),
    ],
)


@pytest.mark.parametrize("oper,target,args,expected", BRIDGE_STR_STR_TESTS)
def test_bridge_str_str(oper, target, args, expected):
    got = getattr(types.BridgeStr(target), oper)(*args)
    assert expected == got
    assert isinstance(got, types.BridgeStr)


BRIDGE_STR_LIST_TESTS = map(
    lambda t: pytest.param(*t[0:], id=t[0]),
    [
        ("partition", "a.b.c", (types.BridgeStr("."),), ("a", ".", "b.c")),
        ("rpartition", "a.b.c", (types.BridgeStr("."),), ("a.b", ".", "c")),
        ("split", "a.b.c", (types.BridgeStr("."), 1), ("a", "b.c")),
        ("rsplit", "a.b.c", (types.BridgeStr("."), 1), ("a.b", "c")),
        ("splitlines", "a\nb\nc", (), ("a", "b", "c")),
    ],
)


@pytest.mark.parametrize("oper,target,args,expected", BRIDGE_STR_LIST_TESTS)
def test_bridge_str_list(oper, target, args, expected):
    got = getattr(types.BridgeStr(target), oper)(*args)
    assert len(got) == len(expected)
    assert all(a == b for a, b in zip(got, expected))


BRIDGE_STR_UNSUPPORTED_TESTS = map(
    lambda t: pytest.param(*t[0:], id=t[0]),
    [
        ("__mod__", "", ("",)),
        ("__rmod__", "", ("",)),
        ("format_map", "", ("",)),
        ("maketrans", "", ()),
        ("translate", "", ()),
    ],
)


@pytest.mark.parametrize("oper,target,args", BRIDGE_STR_UNSUPPORTED_TESTS)
def test_bridge_str_unsupported(oper, target, args):
    with pytest.raises(NotImplementedError):
        getattr(types.BridgeStr(target), oper)(*args)


def test_bridge_str_special():
    with pytest.raises(TypeError):
        print(types.BridgeStr("") + 1)

    iter_ = [c for c in types.BridgeStr("bar")]
    assert all(isinstance(c, types.BridgeStr) for c in iter_)

    with pytest.raises(TypeError):
        types.BridgeStr("").join([None])

    join = types.BridgeStr(".").join([types.BridgeStr("a"), types.Str()])
    assert isinstance(join, types.Join)
    assert join.delim == "."


def test_bridge_str_format():
    val = types.BridgeStr("- {} -").format(types.BridgeStr("foo"))
    assert val == "- foo -"

    val = types.BridgeStr("- {} {:n} -").format(types.BridgeStr("foo"), 42)
    assert val == "- foo 42 -"

    val = types.BridgeStr("- {foo} -").format(foo=types.BridgeStr("foo"))
    assert val == "- foo -"

    val = types.BridgeStr("- {0!r} -").format(types.BridgeStr("foo"))
    assert val == "- 'foo' -"

    val = types.BridgeStr("- {0} {1:n} -").format(types.BridgeStr("foo"), 42)
    assert val == "- foo 42 -"

    with pytest.raises(ValueError):
        types.BridgeStr("{0} {}").format(types.BridgeStr("foo"), 42)

    with pytest.raises(ValueError):
        types.BridgeStr("{} {0}").format(types.BridgeStr("foo"), 42)

    val = types.BridgeStr("- {foo} -").format(foo=types.Str())
    assert isinstance(val, types.Sub)
    assert val.fmt == "- ${A0} -"
    assert isinstance(val.args["A0"], types.Opaque)

    val = types.BridgeStr("- {} {} -").format(types.Str(), types.Str())
    assert isinstance(val, types.Sub)
    assert val.fmt == "- ${A0} ${A1} -"
    assert isinstance(val.args["A0"], types.Opaque)
    assert isinstance(val.args["A1"], types.Opaque)

    with pytest.raises(NotImplementedError):
        types.BridgeStr("{!r}").format(types.Str())

    with pytest.raises(NotImplementedError):
        types.BridgeStr("{:n}").format(types.Str())
