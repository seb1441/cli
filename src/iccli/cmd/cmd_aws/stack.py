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
import time
from contextlib import ContextDecorator, suppress
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, Iterator, List, Mapping, cast

import botocore.exceptions

from ...cloud.aws import config, util

OP_TRANS = dict(ADD="CREATE", MODIFY="UPDATE", REMOVE="DELETE")


class NoChangesError(Exception):
    ...


@dataclass
class State:
    status: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)


class Stack:
    def __init__(self, name: str):
        self.name = util.stack_name(name)
        sess = config.SESSION.get()
        self._client = sess.client("cloudformation")
        self._resource = sess.resource("cloudformation")

    @property
    def exists(self) -> bool:
        with suppress(botocore.exceptions.ClientError):
            stack = self._resource.Stack(self.name)
            stack.load()
            return stack.stack_status != "REVIEW_IN_PROGRESS"
        return False

    @property
    def value(self) -> Any:
        stack = self._resource.Stack(self.name)
        if not stack.outputs:
            return None
        return json.loads(stack.outputs[0]["OutputValue"])

    @property
    def tree(self) -> Mapping:
        tpl = self._client.get_template(StackName=self.name)
        return dict(tpl["TemplateBody"]["Metadata"]["resources"])

    def delete(self, wait=True):
        self._client.delete_stack(StackName=self.name)
        if wait:
            self._client.get_waiter("stack_delete_complete").wait(
                StackName=self.name, WaiterConfig=dict(Delay=1)
            )

    def plan(self, tpl: str, params: Iterable, alter_iam: bool) -> "Plan":
        return Plan(self, tpl, params, alter_iam)

    def events(
        self, state: Dict[str, State], del_on_fail: bool
    ) -> Iterator[Dict[str, State]]:
        stack_id = self._resource.Stack(self.name).stack_id
        pgr = self._client.get_paginator("describe_stack_events")
        start_status = {
            "REVIEW_IN_PROGRESS",
            "CREATE_IN_PROGRESS",
            "UPDATE_IN_PROGRESS",
            "DELETE_IN_PROGRESS",
        }
        end_status = {
            "CREATE_FAILED",
            "CREATE_COMPLETE",
            "ROLLBACK_FAILED",
            "ROLLBACK_COMPLETE",
            "DELETE_FAILED",
            "DELETE_COMPLETE",
            "UPDATE_COMPLETE",
            "UPDATE_ROLLBACK_FAILED",
            "UPDATE_ROLLBACK_COMPLETE",
        }
        last_eid = None
        done = False
        while True:
            new_eid = None
            dirty = False
            new_state = {key: State() for key, v in state.items()}
            for data in pgr.paginate(StackName=stack_id):
                new_eid = new_eid or data["StackEvents"][0]["EventId"]
                for evt in data["StackEvents"]:
                    if evt["EventId"] == last_eid:
                        break
                    dirty = True
                    typ = evt["ResourceType"]
                    status = evt["ResourceStatus"]
                    if typ == "AWS::CloudFormation::Stack":
                        new_state["root"].status.append(status)
                        if status in start_status:
                            break
                        if status in end_status:
                            done = True
                    else:
                        idn = evt["LogicalResourceId"]
                        if idn in new_state:
                            new_state.setdefault(idn, State()).status.append(status)
                        if status.endswith("FAILED") and "ResourceStatusReason" in evt:
                            new_state.setdefault(idn, State()).logs.append(
                                evt["ResourceStatusReason"]
                            )
                else:
                    continue
                break
            last_eid = new_eid
            if dirty:
                for key, new_val in new_state.items():
                    if key in state:
                        old_val = state[key]
                        old_val.status.extend(new_val.status[::-1])
                        old_val.logs.extend(new_val.logs[::-1])
                    else:
                        state[key] = State(
                            status=new_val.status[::-1], logs=new_val.logs[::-1]
                        )
                yield state
                if done:
                    # PyCQA/pylint#2605
                    # pylint: disable=unsubscriptable-object
                    end = state["root"].status[0].partition("_")[0] + "_COMPLETE"
                    last_status = state["root"].status[-1]
                    if del_on_fail:
                        if last_status not in ("DELETE_COMPLETE", end):
                            done = False
                            self.delete(False)
                            continue
                    break
            time.sleep(1)
        for key, val in state.items():
            if len(val.status) == 1:
                # PyCQA/pylint#2605
                # pylint: disable=no-member
                val.status.append("PRISTINE")
        yield state


class Plan(ContextDecorator):
    # pylint: disable=too-many-instance-attributes

    def __init__(self, stack: Stack, tpl: str, params: Iterable, alter_iam: bool):
        self._client = config.SESSION.get().client("cloudformation")
        self._stack = stack
        self._type = "UPDATE" if stack.exists else "CREATE"
        now = datetime.utcnow()
        self._name = f'ic-{now.strftime("%Y-%m-%d--%H-%M-%S")}'
        self._tpl = tpl
        self._params = params
        self._alter_iam = alter_iam
        self._state = cast(Dict[str, State], {"root": State([self._type])})

    def __enter__(self):
        return self

    def __iter__(self) -> Iterator[Dict[str, State]]:
        self._client.create_change_set(
            ChangeSetName=self._name,
            ChangeSetType=self._type,
            StackName=self._stack.name,
            Parameters=self._params,
            Capabilities=("CAPABILITY_NAMED_IAM",) if self._alter_iam else (),
            **{
                "TemplateURL"
                if self._tpl.startswith("http")
                else "TemplateBody": self._tpl
            },
        )
        try:
            self._client.get_waiter("change_set_create_complete").wait(
                ChangeSetName=self._name,
                StackName=self._stack.name,
                WaiterConfig=dict(Delay=1),
            )
        except botocore.exceptions.WaiterError as exc:
            # pylint: disable=no-member
            resp = exc.last_response
            reason = resp["StatusReason"]
            if resp["Status"] == "FAILED" and (
                "The submitted information didn't contain changes." in reason
                or "No updates are to be performed" in reason
            ):
                return
        pgr = self._client.get_paginator("describe_change_set")
        for data in pgr.paginate(ChangeSetName=self._name, StackName=self._stack.name):
            for datum in data["Changes"]:
                change = datum["ResourceChange"]
                action = OP_TRANS[change["Action"].upper()]
                if change.get("Replacement") == "True":
                    action = "REPLACE"
                self._state[change["LogicalResourceId"]] = State([action])
        yield self._state
        self._client.execute_change_set(
            ChangeSetName=self._name, StackName=self._stack.name
        )
        yield from self._stack.events(self._state, self._type == "CREATE")

    def __exit__(self, exc_type, exc, exc_tb):
        if exc_type is None:
            return
        with suppress(botocore.exceptions.ClientError):
            self._client.delete_change_set(
                ChangeSetName=self._name, StackName=self._stack.name
            )
        if self._type == "CREATE":
            self._stack.delete()
