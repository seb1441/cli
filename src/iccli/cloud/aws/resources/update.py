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

"""Download and prepare AWS CloudFormation resource specifications.

AWS CloudFormation resource specifications are JSON-formatted text files
that define the resources and properties that AWS CloudFormation
supports.
Some resources need to be patched to fix invalid shapes (see `patch`).
In this project consistency and uniformity perval. Also, in a first
pass all property names, resource names and attribute names are
extracted. Then, a `camel_to_snake` transformation is applied. One has
to check the `trans.json` file for new entries and confirm that
each transformation is correct (e.g. using git diff + visual control).
The translations file and specification files will be used through the
project to automatically provide up to date and uniform resources upon
import of `ic.aws` or `ic.alexa` modules.

See https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-resource-specification.html

"""

import json
import re
import urllib.request

URL = "https://{dist}.cloudfront.net/latest/CloudFormationResourceSpecification.json"
REFS = {
    "d33vqc0rt9ld30": "ap-northeast-1",  # Asia Pacific (Tokyo)
    "d1ane3fvebulky": "ap-northeast-2",  # Asia Pacific (Seoul)
    "d2zq80gdmjim8k": "ap-northeast-3",  # Asia Pacific (Osaka-Local)
    "d2senuesg1djtx": "ap-south-1",  # Asia Pacific (Mumbai)
    "doigdx0kgq9el": "ap-southeast-1",  # Asia Pacific (Singapore)
    "d2stg8d246z9di": "ap-southeast-2",  # Asia Pacific (Sydney)
    "d2s8ygphhesbe7": "ca-central-1",  # Canada (Central)
    "d1mta8qj7i28i2": "eu-central-1",  # EU (Frankfurt)
    "diy8iv58sj6ba": "eu-north-1",  # EU (Stockholm)
    "d3teyb21fexa9r": "eu-west-1",  # EU (Ireland)
    "d1742qcu2c1ncx": "eu-west-2",  # EU (London)
    "d2d0mfegowb3wk": "eu-west-3",  # EU (Paris)
    "d3c9jyj3w509b0": "sa-east-1",  # South America (São Paulo)
    "d1uauaxba7bl26": "us-east-1",  # US East (N. Virginia)
    "dnwj8swjjbsbt": "us-east-2",  # US East (Ohio)
    "d68hl49wbnanq": "us-west-1",  # US West (N. California)
    "d201a2mn26r7lk": "us-west-2",  # US West (Oregon)
}


def patch(spec):
    props = spec["PropertyTypes"]
    rescs = spec["ResourceTypes"]

    key = "AWS::SSM::Association.ParameterValues"
    if key in props:
        old = props[key]
        props[key] = dict(
            **{
                k: v
                for k, v in old["Properties"]["ParameterValues"].items()
                if k not in ("Documentation", "Required")
            },
            Documentation=old["Documentation"],
        )

    key = "AWS::ServiceDiscovery::Instance"
    if key in rescs:
        old = rescs[key]
        rescs[key]["Properties"]["InstanceAttributes"] = dict(
            **{
                k: v
                for k, v in old["Properties"]["InstanceAttributes"].items()
                if k not in ("PrimitiveType",)
            },
            Type="Map",
            PrimitiveItemType="String",
        )


def camel_to_snake(name):
    sub = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name.replace(".", ""))
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", sub).lower()


def translate(spec, trans):
    for name, types in spec["ResourceTypes"].items():
        vnd, svc, com = name.split("::")
        trans.setdefault(vnd, camel_to_snake(vnd))
        trans.setdefault(svc, camel_to_snake(svc))
        trans.setdefault(com, camel_to_snake(com))
        for attr in types.get("Attributes", {}):
            trans.setdefault(attr, camel_to_snake(attr))
        for prop in types.get("Properties", {}):
            trans.setdefault(prop, camel_to_snake(prop))
    for name, types in spec["PropertyTypes"].items():
        for prop in types.get("Properties", {}):
            trans.setdefault(prop, camel_to_snake(prop))


def update():
    with open("trans.json") as file:
        trans = json.loads(file.read())

    for dist, reg in REFS.items():
        print(f"updating {reg}")
        url = URL.format(dist=dist)
        spec = json.loads(urllib.request.urlopen(url).read().decode())
        patch(spec)
        translate(spec, trans)
        with open(f"{reg}.json", "w") as file:
            file.write(json.dumps(spec))

    with open("trans.json", "w") as file:
        file.write(json.dumps(trans, indent=2, sort_keys=True))


if __name__ == "__main__":
    update()
