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


def b64encode(value):
    import base64

    from ..cloud.aws import types

    if isinstance(value, types.Opaque):
        return types.Base64Encode(value)
    return base64.b64encode(value.encode("utf-8")).decode()


def cidr(block, count, bits):
    import ipaddress

    from ..cloud.aws import types

    if isinstance(block, types.Opaque):
        return types.CIDR(block, count, bits)
    ipn = ipaddress.ip_network(block)
    ips = list(map(str, ipn.subnets(new_prefix=ipn.max_prefixlen - bits)))
    if len(ips) < count:
        raise IndexError("list index out of range")
    return ips[:count]


def outputs(name):
    from ..core import config as core_config
    from ..cloud.aws import config

    if core_config.MODE.get() != core_config.Mode.ICP:
        raise NotImplementedError(f"{outputs.__name__} only available in .icp files")

    cfn = config.SESSION.get().client("cloudformation")
    stacks = cfn.describe_stacks(StackName=name)
    if "Outputs" not in stacks["Stacks"][0]:
        return None
    return {
        output["OutputKey"]: output["OutputValue"]
        for output in stacks["Stacks"][0]["Outputs"]
    }
