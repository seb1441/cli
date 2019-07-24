# Copyright 2019 Farzad Senart and Lionel Suss. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


def sensitive(value: str):
    import base64
    import hashlib

    from ..core import config as core_config
    from ..cloud.aws import config, types

    if core_config.MODE.get() != core_config.Mode.ICP:
        raise NotImplementedError(f"{sensitive.__name__} only available in .icp files")

    hash_ = hashlib.sha1(value.encode("utf-8"))
    name = base64.b32encode(hash_.digest()[:5]).lower().decode("utf-8")
    param = types.Sensitive(name, value)
    config.SENSITIVES.get().append(param)
    return param


def brick(name: str):
    import json

    from ..core import config as core_config
    from ..cloud.aws import config, util

    if core_config.MODE.get() != core_config.Mode.ICP:
        raise NotImplementedError(f"{brick.__name__} only available in .icp files")

    cfn = config.SESSION.get().client("cloudformation")
    stacks = cfn.describe_stacks(StackName=util.stack_name(name))
    if "Outputs" not in stacks["Stacks"][0]:
        return None
    return json.loads(stacks["Stacks"][0]["Outputs"][0]["OutputValue"])


def environ(name: str, default=None):
    import os
    from ..core import config as core_config

    if core_config.MODE.get() != core_config.Mode.ICP:
        raise NotImplementedError(f"{brick.__name__} only available in .icp files")
    return os.getenv(name, default)
