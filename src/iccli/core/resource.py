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

import base64
import hashlib
import logging
import re
from contextvars import ContextVar, copy_context
from functools import wraps
from types import MethodType
from typing import Any, Iterable, Iterator, MutableMapping, Optional, cast

LOGGER = logging.getLogger(__name__)
PARENT: ContextVar[Optional["Resource"]] = ContextVar("parent")


class Resource:
    """The node in the resources tree.

    It ensures encapsulation and shareability of simple or complex
    coordination between native cloud resources. It is one of the core
    concepts of the project.
    The identity of a resource is tied to its name and its parents'
    lineage. Also, for the same name, the identity is driven by the
    level in the hierarchy. At the same level, the order doesn't matter.

    """

    # pylint: disable=invalid-name

    def __init__(self, name: str):
        check_name(name)
        self._name = name
        self._value = cast(Optional[Any], None)
        self._children = cast(MutableMapping[str, "Resource"], {})
        self._parent = PARENT.get(None)
        if self._parent:
            # pylint: disable=protected-access
            if name in self._parent._children:
                LOGGER.warning(
                    "%r node has been erased",
                    ".".join(self._parent._children[name].lineage),
                )
            self._parent._children[name] = self

    @property
    def name(self):
        return self._name

    @property
    def lineage(self):
        return (*getattr(self._parent, "lineage", ()), self.name)

    @property
    def id(self) -> str:
        hash_ = hashlib.sha1("".join(self.lineage).encode("utf-8"))
        return base64.b32encode(hash_.digest()[:5]).lower().decode("utf-8")

    @property
    def children(self) -> Iterable["Resource"]:
        return list(self._children.values())

    def __iter__(self) -> Iterator["Resource"]:
        yield self
        for child in self.children:
            yield from child

    def __hash__(self):
        return hash(self.lineage)

    def __eq__(self, other):
        if not isinstance(other, Resource):
            return NotImplemented  # pragma: no cover
        return self.lineage == other.lineage


class ResourceInfo:
    def __init__(self, **kwargs):
        self._items = {}

        def contextify(wrapped):
            curr = PARENT.get()

            @wraps(wrapped)
            def wrapper(*args, **kwds):
                def impl():
                    PARENT.set(curr)
                    return wrapped(*args, **kwds)

                return copy_context().run(impl)

            return wrapper

        self._attrs = {
            k: MethodType(contextify(v), self) for k, v in kwargs.items() if callable(v)
        }
        self._items.update({k: v for k, v in kwargs.items() if not k in self._attrs})

    def __getattr__(self, attr: str):
        if attr not in self._attrs:
            return super().__getattribute__(attr)
        return self._attrs[attr]

    def __len__(self, *args, **kwargs):
        return self._items.__len__(*args, **kwargs)

    def __getitem__(self, *args, **kwargs) -> Any:
        return self._items.__getitem__(*args, **kwargs)

    def __setitem__(self, *args, **kwargs):
        return self._items.__setitem__(*args, **kwargs)

    def __delitem__(self, *args, **kwargs):
        return self._items.__delitem__(*args, **kwargs)

    def __contains__(self, *args, **kwargs):
        return self._items.__contains__(*args, **kwargs)

    def __iter__(self, *args, **kwargs):
        return self._items.__iter__(*args, **kwargs)

    def clear(self, *args, **kwargs):
        return self._items.clear(*args, **kwargs)

    def copy(self, *args, **kwargs):
        return self._items.copy(*args, **kwargs)

    @classmethod
    def fromkeys(cls, *args, **kwargs):
        return dict.fromkeys(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self._items.get(*args, **kwargs)

    def items(self, *args, **kwargs):
        return self._items.items(*args, **kwargs)

    def keys(self, *args, **kwargs):
        return self._items.keys(*args, **kwargs)

    def pop(self, *args, **kwargs):
        return self._items.pop(*args, **kwargs)

    def popitem(self, *args, **kwargs):
        return self._items.popitem(*args, **kwargs)

    def setdefault(self, *args, **kwargs):
        return self._items.setdefault(*args, **kwargs)

    def update(self, *args, **kwargs):
        return self._items.update(*args, **kwargs)

    def values(self, *args, **kwargs):
        return self._items.values(*args, **kwargs)


def resource(wrapped):
    """Decorate a resource implementation to integrate it in the
    resource tree.

    It links parents and children and return the implementation value
    to the caller unless there is no parent. In the latter case, this
    'hack' allows to access the root node.

    """

    @wraps(wrapped)
    def wrapper(*args, **kwargs):
        curr = Resource(next(iter(args), ""))

        def impl():
            PARENT.set(curr)
            return wrapped(*args[1:], **kwargs)

        # pylint: disable=protected-access
        curr._value = copy_context().run(impl)
        return curr._value if curr._parent else curr

    return wrapper


def check_name(val: Any):
    """Check that the resource name is valid.

    It must start with a lower case letter and be composed of lowercase
    alphanumeric characters or '_'.

    """
    err = None
    if not val:
        err = "name is required"
    elif not isinstance(val, str):
        err = "must be a string"
    elif not val[0].islower():
        err = "must start with lowercase"
    elif any(c.isupper() for c in val):
        err = "mixed case, expected lowercase"
    elif not re.fullmatch(r"[a-z]+[a-z0-9_]*", val):
        err = "invalid chars, expected [a-z0-9_]"
    if err:
        raise ValueError(f"malformed resource name {val!r}: {err}")
