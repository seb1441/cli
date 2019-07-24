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
#
# This file incorporates work covered by the following copyright and
# permission notice (`BridgeStr.format` function):
#
#   Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009,
#   2010,2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019 Python
#   Software Foundation; All Rights Reserved
#
#   1. This LICENSE AGREEMENT is between the Python Software Foundation
#   ("PSF"), and the Individual or Organization ("Licensee") accessing and
#   otherwise using this software ("Python") in source or binary form and
#   its associated documentation.
#
#   2. Subject to the terms and conditions of this License Agreement, PSF hereby
#   grants Licensee a nonexclusive, royalty-free, world-wide license to reproduce,
#   analyze, test, perform and/or display publicly, prepare derivative works,
#   distribute, and otherwise use Python alone or in any derivative version,
#   provided, however, that PSF's License Agreement and PSF's notice of copyright,
#   i.e., "Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
#   2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019 Python Software Foundation;
#   All Rights Reserved" are retained in Python alone or in any derivative version
#   prepared by Licensee.
#
#   3. In the event Licensee prepares a derivative work that is based on
#   or incorporates Python or any part thereof, and wants to make
#   the derivative work available to others as provided herein, then
#   Licensee hereby agrees to include in any such work a brief summary of
#   the changes made to Python.
#
#   4. PSF is making Python available to Licensee on an "AS IS"
#   basis.  PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR
#   IMPLIED.  BY WAY OF EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND
#   DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS
#   FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON WILL NOT
#   INFRINGE ANY THIRD PARTY RIGHTS.
#
#   5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON
#   FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS
#   A RESULT OF MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON,
#   OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.
#
#   6. This License Agreement will automatically terminate upon a material
#   breach of its terms and conditions.
#
#   7. Nothing in this License Agreement shall be deemed to create any
#   relationship of agency, partnership, or joint venture between PSF and
#   Licensee.  This License Agreement does not grant permission to use PSF
#   trademarks or trade name in a trademark sense to endorse or promote
#   products or services of Licensee, or any third party.
#
#   8. By copying, installing or otherwise using Python, Licensee
#   agrees to be bound by the terms and conditions of this License
#   Agreement.

import string
from typing import Any, Dict, Iterable, Mapping, Tuple, Type, Union

# pylint: disable=too-few-public-methods
# pylint: disable=no-self-use


class Opaque:
    """Base class for all types that are only available at provision
    time at the AWS CloudFormation side.

    The purpose of this type is to unify remote types with local types
    so that the user can play with them seamlessly.

    """

    def __bool__(self):
        raise TypeError("opaque: undefined truth value")


class Bool(Opaque):
    ...


class Int(Opaque):
    ...


class Str(Opaque):
    def split(self, sep: str = ""):
        return Split(sep, self)

    def replace(self, old: str, new: str, count=None):
        if count is not None:
            raise NotImplementedError("opaque: str replace count")
        return Join(new, self.split(old))

    def __add__(self, other):
        if not isinstance(other, (str, Opaque)):
            return NotImplemented
        return BridgeStr("").join([self, other])


class List(Opaque):
    select: Type["Select"]

    def __class_getitem__(cls, item: Type[Opaque]) -> Type["List"]:
        return type(List.__name__, (List,), dict(select=Select[item]))  # type: ignore

    def __getitem__(self, item: int) -> "Select":
        return self.select(item, self)


class Attr(Opaque):
    name: str

    def __class_getitem__(
        cls, item: Tuple[Type[Opaque], str]
    ) -> Union[Type["Attr"], Type[Opaque]]:
        return type(Attr.__name__, (Attr, item[0]), dict(name=item[1]))

    def __init__(self, rid: str):
        self.rid = rid


class Join(Str):
    def __init__(self, delim: str, args: Union[List, Iterable[Union[Str, str]]]):
        self.delim = delim
        self.args = args

class Ref(Str):
    def __init__(self, rid: str):
        self.rid = rid


class Select(Opaque):
    def __class_getitem__(
        cls, item: Type[Opaque]
    ) -> Union[Type["Select"], Type[Opaque]]:
        return type(Select.__name__, (Select, item), {})

    def __init__(self, item: int, args: List):
        if not isinstance(item, int):
            raise TypeError("opaque: list indices must be integers")
        self.item = item
        self.args = args


class Sensitive(Str):
    def __init__(self, name: str, value: Any):
        if not isinstance(value, str):
            raise TypeError(f"sensitive: expected 'str' got {type(value).__name__!r}")
        self.name = name
        self.value = value


class Split(List[Str]):  # type: ignore
    def __init__(self, sep: str, arg: Str):
        self.sep = sep
        self.arg = arg


class Sub(Str):
    def __init__(self, fmt: str, args: Mapping[str, Opaque]):
        self.fmt = fmt
        self.args = args


class AvailabilityZones(List[Str]):  # type: ignore
    def __init__(self, region: str = None):
        self.region = region or Region()


class Base64Encode(Str):
    def __init__(self, arg: Opaque):
        self.arg = arg


class CIDR(List[Str]):  # type: ignore
    def __init__(self, block: Opaque, count: int, bits: int):
        self.block = block
        self.count = count
        self.bits = bits


class AccountID(Str):
    ...


class NotificationARNs(List[Str]):  # type: ignore
    ...


class Partition(Str):
    ...


class Region(Str):
    ...


class StackID(Str):
    ...


class URLSuffix(Str):
    ...


class BridgeStr(str):
    # pylint: disable=too-many-public-methods,arguments-differ

    def __getitem__(self, *args, **kwargs):
        return BridgeStr(super().__getitem__(*args, **kwargs))

    def __add__(self, other):
        if not isinstance(other, (str, Opaque)):
            return NotImplemented
        return BridgeStr("").join([self, other])

    def __iter__(self, *args, **kwargs):
        yield from map(BridgeStr, super().__iter__(*args, **kwargs))

    def __mod__(self, *args, **kwargs):
        raise NotImplementedError

    def __mul__(self, *args, **kwargs):
        return BridgeStr(super().__mul__(*args, **kwargs))

    def __rmod__(self, *args, **kwargs):
        raise NotImplementedError

    def __rmul__(self, *args, **kwargs):
        return BridgeStr(super().__rmul__(*args, **kwargs))

    def capitalize(self, *args, **kwargs):
        return BridgeStr(super().capitalize(*args, **kwargs))

    def casefold(self, *args, **kwargs):
        return BridgeStr(super().casefold(*args, **kwargs))

    def center(self, *args, **kwargs):
        return BridgeStr(super().center(*args, **kwargs))

    def expandtabs(self, *args, **kwargs):
        return BridgeStr(super().expandtabs(*args, **kwargs))

    def format(self, *args, **kwargs):
        # See https://github.com/python/cpython/tree/8713aa6/Lib/string.py
        formatter = string.Formatter()
        fmt, vals = [], {}
        auto = 0
        for lit, field, spec, conv in formatter.parse(self):
            fmt.append(lit)
            if field is None:
                continue
            if field == "":
                if auto is False:
                    raise ValueError(
                        "cannot switch from manual field specification "
                        "to automatic field numbering"
                    )
                field = str(auto)
                auto += 1
            elif field.isdigit():
                if auto:
                    raise ValueError(
                        "cannot switch from automatic field numbering "
                        "to manual field specification"
                    )
                auto = False
            obj, _ = formatter.get_field(field, args, kwargs)
            if isinstance(obj, Opaque):
                if spec or conv:
                    err = f"{lit}{{{field}"
                    err += f"!{conv}" if conv else ""
                    err += f":{spec}" if spec else ""
                    err += "}"
                    raise NotImplementedError(
                        f"opaque: spec and conversion not supported: '{err}'"
                    )
                name = f"A{len(vals)}"
                fmt.append(f"${{{name}}}")
                vals[name] = obj
            else:
                obj = formatter.convert_field(obj, conv)
                obj = formatter.format_field(obj, spec)
                fmt.append(obj)
        if vals:
            return Sub("".join(fmt), vals)
        return "".join(fmt)

    def format_map(self, *args, **kwargs):
        raise NotImplementedError

    def join(self, iterable):
        none_idx = next((i for i, v in enumerate(iterable) if v is None), -1)
        if none_idx != -1:
            raise TypeError(
                f"sequence item {none_idx}: expected str instance, NoneType found"
            )
        if not any(isinstance(arg, Opaque) for arg in iterable):
            return BridgeStr(super().join(iterable))
        return Join(self, iterable)

    def ljust(self, *args, **kwargs):
        return BridgeStr(super().ljust(*args, **kwargs))

    def lower(self, *args, **kwargs):
        return BridgeStr(super().lower(*args, **kwargs))

    def lstrip(self, *args, **kwargs):
        return BridgeStr(super().lstrip(*args, **kwargs))

    @staticmethod
    def maketrans(*args, **kwargs):
        raise NotImplementedError

    def partition(self, *args, **kwargs):
        org = super().partition(*args, **kwargs)
        return type(org)(map(BridgeStr, org))

    def replace(self, *args, **kwargs):
        return BridgeStr(super().replace(*args, **kwargs))

    def rjust(self, *args, **kwargs):
        return BridgeStr(super().rjust(*args, **kwargs))

    def rpartition(self, *args, **kwargs):
        org = super().rpartition(*args, **kwargs)
        return type(org)(map(BridgeStr, org))

    def rsplit(self, *args, **kwargs):
        org = super().rsplit(*args, **kwargs)
        return type(org)(map(BridgeStr, org))

    def rstrip(self, *args, **kwargs):
        return BridgeStr(super().rstrip(*args, **kwargs))

    def split(self, *args, **kwargs):
        org = super().split(*args, **kwargs)
        return type(org)(map(BridgeStr, org))

    def splitlines(self, *args, **kwargs):
        org = super().splitlines(*args, **kwargs)
        return type(org)(map(BridgeStr, org))

    def strip(self, *args, **kwargs):
        return BridgeStr(super().strip(*args, **kwargs))

    def swapcase(self, *args, **kwargs):
        return BridgeStr(super().swapcase(*args, **kwargs))

    def title(self, *args, **kwargs):
        return BridgeStr(super().title(*args, **kwargs))

    def translate(self, *args, **kwargs):
        raise NotImplementedError

    def upper(self, *args, **kwargs):
        return BridgeStr(super().upper(*args, **kwargs))

    def zfill(self, *args, **kwargs):
        return BridgeStr(super().zfill(*args, **kwargs))


def fstr(args):
    if not any(isinstance(a, Opaque) for a in args):
        return BridgeStr("".join(args))
    fmt = []
    vals: Dict[str, Any] = {}
    for arg in args:
        if isinstance(arg, Opaque):
            name = f"A{len(vals)}"
            fmt.append(f"${{{name}}}")
            vals[name] = arg
        else:
            fmt.append(arg)
    return Sub("".join(fmt), vals)


def fval(obj, conv, spec):
    if isinstance(obj, Opaque):
        if spec or conv > -1:
            err = "{"
            err += f"!{chr(conv)}" if conv else ""
            err += f":{spec}" if spec else ""
            err += "}"
            raise NotImplementedError(
                f"opaque: spec and conversion not supported: '{err}'"
            )
        return obj
    formatter = string.Formatter()
    if conv > -1:
        obj = formatter.convert_field(obj, chr(conv))
    return formatter.format_field(obj, spec or "")
