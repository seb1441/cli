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

from . import resource

# pylint: disable=protected-access


def test_identity():
    res1 = resource.Resource("r1")
    res1._value = "foo"
    res2 = resource.Resource("r1")
    res2._value = "bar"
    res3 = resource.Resource("r3")
    res3._value = "baz"
    res3._parent = res1
    res4 = resource.Resource("r3")
    res4._value = "qux"
    res4._parent = res2
    res1._children["res3"] = res3
    res4._children["res1"] = res1

    assert res1 == res2
    assert hash(res1) == hash(res2)
    assert res1.id == res2.id

    assert res3 == res4
    assert hash(res3) == hash(res4)
    assert res3.id == res4.id


def test_iterator():
    root = resource.Resource("root")
    child1 = resource.Resource("child1")
    child11 = resource.Resource("child11")
    root._children["child1"] = child1
    child1._children["child11"] = child11

    assert tuple(r for r in root) == (root, child1, child11)


CHECK_NAME_INVALID_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [("empty", ""), ("type", 1), ("start", "A"), ("mixed", "aBc"), ("invalid", "a-b")],
)


@pytest.mark.parametrize("val", CHECK_NAME_INVALID_TESTS)
def test_check_name_invalid(val):
    with pytest.raises(ValueError):
        resource.check_name(val)


def test_decorator():
    # pylint: disable=E,W,R,C
    @resource.resource
    def res1():
        return res2("res2", x=1) + 1

    @resource.resource
    def res2(x):
        return res3("res3", y=x + 1) + 2

    @resource.resource
    def res3(y):
        return y + 3

    root = res1("res1")
    values = tuple(r._value for r in root)
    rescs = [r for r in root]

    assert values == (8, 7, 5)
    assert resource.PARENT.get(None) is None
    assert rescs[0] is rescs[1]._parent
    assert rescs[1] is rescs[2]._parent


INFO_DICT_TESTS = map(
    lambda t: pytest.param(*t[0:], id=t[0]),
    [
        ("__len__", dict(a=1), ()),
        ("__getitem__", dict(a=1), ("a",)),
        ("__setitem__", dict(a=1), ("a", 3)),
        ("__delitem__", dict(a=1), ("a",)),
        ("__contains__", dict(a=1), ("a",)),
        # ("__iter__", dict(a=1), ()),
        ("clear", dict(a=1), ()),
        ("copy", dict(a=1), ()),
        ("fromkeys", dict(a=1), ("b", 1)),
        ("get", dict(a=1), ("a")),
        ("items", dict(a=1), ()),
        ("keys", dict(a=1), ()),
        ("pop", dict(a=1), ("a",)),
        ("popitem", dict(a=1), ()),
        ("setdefault", dict(a=1), ("b", 3)),
        ("update", dict(a=1), (dict(b=3),)),
        # ("values", dict(a=1), ()),
    ],
)


@pytest.mark.parametrize("mth,cons,pars", INFO_DICT_TESTS)
def test_info_dict(mth, cons, pars):
    res = resource.ResourceInfo(**cons)
    assert getattr(res, mth)(*pars) == getattr(cons, mth)(*pars)
    assert res._items == cons


def test_info_extra():
    res = resource.ResourceInfo(a=1)
    exp = dict(a=1)
    assert next(iter(res)) == next(iter(exp))
    assert tuple(res.values()) == tuple(exp.values())

    with pytest.raises(AttributeError):
        print(res.dummy)
