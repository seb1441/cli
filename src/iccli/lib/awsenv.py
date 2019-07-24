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

from ..cloud.aws.types import (
    AccountID,
    AvailabilityZones,
    NotificationARNs,
    Partition,
    Region,
    StackID,
    URLSuffix,
)

# pylint: disable=invalid-name

account_id = AccountID()
availability_zones = AvailabilityZones()
notification_arns = NotificationARNs()
partition = Partition()
region = Region()
stack_id = StackID()
url_suffix = URLSuffix()
