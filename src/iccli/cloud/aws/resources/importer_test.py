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
import sys

import pytest

from ....core import config as base_config
from ....core import importer as base_importer
from .. import config
from . import importer, load


def test_import():
    base_config.MODE.set(base_config.Mode.IC)
    config.REGION.set("us-east-1")
    sys.meta_path.insert(0, base_importer.LibFinder())
    sys.meta_path.insert(1, importer.Finder())

    spec = load(config.REGION.get())
    for vnd in spec:
        vnd_mod = importlib.import_module(f"icl.{vnd}")
        for svc in spec[vnd]:
            assert hasattr(vnd_mod, svc)
            svc_mod = importlib.import_module(f"icl.{vnd}.{svc}")
            for com in spec[vnd][svc]:
                assert hasattr(svc_mod, com)
                assert spec[vnd][svc][com] == getattr(svc_mod, com)

    with pytest.raises(ImportError):
        importlib.import_module(f"icl.dummy")

    with pytest.raises(ImportError):
        importlib.import_module(f"icl.aws.dummy")

    with pytest.raises(ImportError):
        importlib.import_module(f"icl.aws.cloudformation.dummy")
