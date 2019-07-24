<a id="top" name="top"></a>

# IC
> Bricks and mortar for :cloud: developers.

The IC project combines a language, a public index, and a set of tools 
to empower every developer to create composable cloud-native 
infrastructures, share, and collaborate, irrespective of cloud providers.

# General Information

- Website: https://ic.dev
- Source code: https://github.com/icdotdev/cli
- Issue tracker: https://github.com/icdotdev/cli/issues
- Documentation: https://docs.ic.dev

# Glimpse

## Syntax

Let's create a simple web server. 

```python
from ic import aws, awsutil


USER_DATA = """#!/usr/bin/env bash
echo "Hello, World!" > index.html
nohup python -m SimpleHTTPServer 80 &"""


@resource
def brick():
    security_group = aws.ec2.security_group(
        "security_group",
        group_description="Enable HTTP access via port 80",
        security_group_ingress=[
            dict(cidr_ip="0.0.0.0/0", from_port=80, to_port=80, ip_protocol="tcp")
        ],
    )
    instance = aws.ec2.instance(
        "instance",
        instance_type="t2.micro",
        image_id="ami-0cc96feef8c6bbff3",
        security_groups=[security_group["ref"]],
        user_data=awsutil.b64encode(USER_DATA),
    )
    return f"http://{instance['public_ip']}"
```

**What happened?**

- **L9**: we create a new IC resource, a virtual unit of infrastructure
- **L11 & L18**: we create two native AWS specific resources
- **L22**: we reference a previously created resource
- **L23**: we use an AWS specific function provided by the IC Standard 
  Library imported at L1
- **L25**: we return a formatted string with a dynamic attribute as the 
  value of our resource

## Community

Above, we did all the hard work by ourselves :sweat_smile:. However, 
maybe someone in the community has already taken this effort.

```bash
$ ic search hello world
──────────────────────────────────────────────────────────────────────
fsenart.hello_world
My first IC brick

MIT • v0.2.0 • 42 days ago
──────────────────────────────────────────────────────────────────────
```

Luckily, fsenart has already made if for us :heart_eyes: ! Let's not 
reinvent the wheel and deploy it right from the IC Public Index.

```bash
$ ic aws up fsenart.hello_world demo
```

That's it! We can now retrieve the dynamic value returned by our 
resource to access the web server. 

```bash
$ ic aws value demo
"http://1.2.3.4"
```

## Beyond

Finally, let's customize the brick we've found earlier.

```python
from fsenart import hello_world

@resource
def brick():
    return hello_world.brick("hello_me", message="Hello, Me!")
```

And share it with the community.

```bash
$ ic publish
```

# Copyright and License

Copyright 2019 Farzad Senart and Lionel Suss. All rights reserved.

Unless otherwise stated, the source code is licensed under the 
[GNU Affero General Public License Version 3 (AGPLv3)](LICENSE).
> If you use IC to create your infrastructure, then your source code 
  **DOES NOT** need to be licensed under GPL.<br/><br/>
  The IC Standard Library (the only API between your source code and the 
  AGPL licensed IC source code) is licensed under the 
  [Apache License Version 2](src/iccli/lib/LICENSE).


Unless otherwise stated, the documentation is licensed under the 
[Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/). 