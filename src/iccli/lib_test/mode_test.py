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

from ..core import config as core_config
from ..lib import awsutil, util

MODE_INVALID_TESTS = map(
    lambda t: pytest.param(*t[1:], id=t[0]),
    [
        ("util.sensitive", util.sensitive, core_config.Mode.IC, ["dummy"]),
        ("util.brick", util.brick, core_config.Mode.IC, ["dummy"]),
        ("util.environ", util.environ, core_config.Mode.IC, ["dummy"]),
        ("awsutil.outputs", awsutil.outputs, core_config.Mode.IC, ["dummy"]),
    ],
)


@pytest.mark.parametrize("func,mode,args", MODE_INVALID_TESTS)
def test_mode_invalid(func, mode, args):
    core_config.MODE.set(mode)
    with pytest.raises(NotImplementedError):
        func(*args)
