<a id="top" name="top"></a>

<h1 align="center">
    <p align="center"><a href="https://ic.dev">ic.dev</a></p>
    <img src="https://ic.dev/img/hero.gif">
</h1>

<p align="center">
    <a href="https://pypi.org/project/iccli/" alt="PyPI version">
        <img src="https://img.shields.io/pypi/v/iccli.svg">
    </a>
    <a href="https://pypi.org/project/iccli/" alt="PyPI version">
        <img src="https://img.shields.io/pypi/status/iccli.svg">
    </a>
    <a href="https://pypi.org/project/iccli/" alt="Python versions">
        <img src="https://img.shields.io/pypi/pyversions/iccli.svg">
    </a>
    <a href="https://github.com/icdotdev/cli#license" alt="License">
        <img src="https://img.shields.io/badge/license-AGPL--3.0%2FApache--2.0-green">
    </a>
    <a href="https://slack.ic.dev" alt="Slack">
        <img src="https://slack.ic.dev/badge.svg">
    </a>
    <a href="https://twitter.com/icdotdev" alt="Twitter">
        <img src="https://img.shields.io/twitter/follow/icdotdev?style=social">
    </a>
</p>

## Introduction

> Read the introduction post on [Medium][medium-announce].

[ic.dev][ic-home] is an open source project that makes it easy to
compose, share, and deploy cloud infrastructure bricks.

- **Native**: As we rely on the official [AWS CloudFormation Resource
  Specification][cfn-spec], you have access to 100% of AWS resources. We
  also compile your code to native AWS CloudFormation, so that you can
  always access the raw templates and benefit from state management by
  AWS CloudFormation.
- **Familiar**: Write your infrastructure logic in Python, the
  well-known easy-to-use, powerful, and versatile language. Use modern
  software development techniques and forget about all [AWS
  CloudFormation quirks and weirdness][cfn-intrinsic] thanks to our
  [smart purpose-built parser][ic-parser].
- **Open**: Get involved and be part of the adventure. Join our [Slack
  channel][ic-slack], browse our [GitHub repositories][ic-github],
  [submit issues][ic-issues] or [pull requests][ic-pulls] for bugs you
  find, and ask for any new features you may want to be implemented.
- **Modular**: [Everything is a resource][ic-rescs]. Whether it be a
  simple Amazon S3 bucket or a serverless e-commerce app, combine any
  resources into more high-level bricks. View your whole infrastructure
  as a nested tree of arbitrary level and gain unprecedented insights
  about your configuration.
- **Community**: Need a particular service or even a whole application?
  Don't reinvent the wheel. We ship with a [free and public
  index][ic-index] to allow authors and contributors to make their bricks
  available for the community to use under open source license terms.
  Before writing a line of code, search in the index!

[Learn how to use IC CLI for creating your infrastructure][ic-start].

## Installation

IC CLI is available as the [`iccli` package][ic-pypi] on
[PyPI][pypi-home].

We also have an [open documentation][ic-website] to make [getting
started][ic-start] with IC CLI even easier. If you need any further
assistance, come and talk to the community on our [Slack
channel][ic-slack].

## Documentation

You can find the IC CLI documentation [on the website][ic-home].

Check out the [Getting Started][ic-start] page for a quick overview.

The documentation is divided into several sections:

- [Getting Started](https://ic.dev/docs/en/installation)
- [Resources](https://ic.dev/docs/en/resources)
- [Assets](https://ic.dev/docs/en/assets)
- [Parser](https://ic.dev/docs/en/parser)
- [Dependencies](https://ic.dev/docs/en/dependencies)
- [Standard Library](https://ic.dev/docs/en/stdlib)

You can improve it by sending pull requests to [this
repository][ic-website].

## License

Copyright 2019 Farzad Senart and Lionel Suss. All rights reserved.

Unless otherwise stated, the source code is licensed under the
[GNU Affero General Public License Version 3 (AGPLv3)][ic-license].

However, the [IC Standard Library][ic-stdlib], the only API between your
source code and the AGPLv3 licensed source code is licensed under the
[Apache License Version 2.0][ic-stdlib-license]. Therefore, when using
the IC CLI to author your infrastructure resources, **you are NOT
REQUIRED to release your source code under a GPL license**.

[ic-license]: https://github.com/icdotdev/cli/blob/master/LICENSE
[ic-stdlib]: https://github.com/icdotdev/cli/tree/master/src/iccli/lib
[ic-stdlib-license]: https://github.com/icdotdev/cli/tree/master/src/iccli/lib/LICENSE
[ic-parser]: https://ic.dev/docs/en/parser/
[ic-slack]: https://slack.ic.dev
[ic-github]: https://github.com/icdotdev
[ic-issues]: https://github.com/icdotdev/cli/issues
[ic-pulls]: https://github.com/icdotdev/cli/pulls
[ic-rescs]: https://ic.dev/docs/en/resources
[ic-index]: https://ic.dev/docs/en/community
[ic-start]: https://ic.dev/docs/en/installation
[ic-pypi]: https://pypi.org/project/iccli
[ic-home]: https://ic.dev
[ic-website]: https://github.com/icdotdev/icdotdev
[cfn-spec]: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-resource-specification.html
[cfn-intrinsic]: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference.html
[pypi-home]: https://pypi.org
[medium-announce]: https://medium.com/icdotdev/introducing-icdotdev-d9335fb1bad
