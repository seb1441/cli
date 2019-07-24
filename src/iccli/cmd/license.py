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
import pathlib
import urllib.request

URL = "https://raw.githubusercontent.com/spdx/license-list-data//master/json/licenses.json"


def update():
    raw = json.loads(urllib.request.urlopen(URL).read().decode())
    ids = {l["licenseId"] for l in raw["licenses"]}
    pathlib.Path("licenses.json").write_text(json.dumps(list(ids), sort_keys=True))


if __name__ == "__main__":
    update()
