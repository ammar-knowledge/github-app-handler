"""Class to help apps to create testing emulating webhooks events"""

import inspect
import json
import os
from collections import defaultdict
from itertools import zip_longest
from typing import Any, Optional, TypeVar
from unittest import TestCase as UnittestTestCase
from unittest.mock import Mock, call, patch

from github import GithubException
from github.CheckRun import CheckRun
from github.Repository import Repository

from githubapp import EventCheckRun
from githubapp.event_check_run import CheckRunConclusion, CheckRunStatus
from githubapp.events.event import Event
from githubapp.test_helper.spy import spy

T = TypeVar("T")


def recursive_update(main_dict: dict[str, Any], updates: dict[str, Any]) -> None:
    """
    Recursively updates the main_dict with the given updates.

    :param main_dict: The dictionary to be updated.
    :param updates: The dictionary with the updates to be applied.
    :return: None.
    """
    for key, value in updates.items():
        if isinstance(value, dict):
            # get node or create one
            node = main_dict.setdefault(key, {})
            recursive_update(node, value)
        else:
            main_dict[key] = value


def get_config(*_args, **_kwargs) -> Mock:
    """Mock the reading of the config file"""
    return Mock(decoded_content="")


def edit(self: CheckRun, **attributes) -> None:
    """Edit the object's attributes using the provided attributes."""
    attributes.setdefault("output", {})
    for k, v in self.output.raw_data.items():
        attributes["output"].setdefault(k, v)
    self._useAttributes(attributes)


class TestCase(UnittestTestCase):
    """Class to help apps to create testing emulating webhooks events"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.client = None
        self.event = None
        defaults_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "defaults.json")
        self.defaults = self.get_info_from_file(defaults_file)
        self._check_runs = defaultdict(dict)
        self._sub_run_call_index = 0

    def get_filename(self) -> Optional[str]:
        """Returns the filename for the test."""
        # Get the module object
        module = __import__(self.__class__.__module__)
        if hasattr(module, "__file__"):
            test_dir = os.path.dirname(os.path.abspath(module.__file__))
            class_name = self.__class__.__name__
            method_name = self._testMethodName
            return os.path.join(test_dir, f"{class_name}.{method_name}.json")
        return None

    def get_info_from_file(self, filename: str = None) -> dict[str, Any]:
        """Retrieve information from a json file."""
        filename = filename or self.get_filename()
        if os.path.exists(filename):
            with open(filename, "r") as stream:
                data = json.load(stream)
            return data
        return {}

    @staticmethod
    def create_github_exception(message: str, status: int = 500) -> GithubException:
        """
        Simple way to create a GithubException for tests

        return a GithubException(STATUS, data={"errors": [{"message": MESSAGE}]})
        """
        return GithubException(status, data={"errors": [{"message": message}]})

    @staticmethod
    def sub_run_call(name: str, title: str, summary: str = "") -> call:
        final_summary = f"{name}: {title}"
        if summary:
            final_summary += f"\n{summary}"

        return call(title=title, summary=final_summary)

    def create_sub_runs(self, check_run_name: str, *sub_run_names: str) -> None:
        """Create sub runs for a given check run."""
        sub_runs = self._check_runs[check_run_name]
        for sub_run_name in sub_run_names:
            sub_runs[sub_run_name] = EventCheckRun.SubRun(Mock(spec=EventCheckRun), sub_run_name)

    def assert_sub_run_call(self, check_run_name: str, sub_run_name: str, **params) -> None:
        check_run = self.get_check_run(check_run_name)
        sub_runs = self._check_runs[check_run_name]
        if sub_run_name not in sub_runs:
            sub_runs[sub_run_name] = EventCheckRun.SubRun(Mock(spec=EventCheckRun), sub_run_name)

        sub_run = sub_runs[sub_run_name]
        for k, v in params.items():
            setattr(sub_run, k, v)

        final_summary = EventCheckRun.build_summary(sub_runs.values())
        params.pop("summary", None)

        sub_run_call = call(summary=final_summary, **params)

        try:
            assert check_run.update.mock_calls[self._sub_run_call_index] == sub_run_call
        except IndexError:
            raise AssertionError("Missing call", sub_run_call)
        self._sub_run_call_index += 1

    def assert_no_check_run(self, name: str) -> None:
        """
        Asserts that no check run exists with the given name.
        :raise AssertionError: If there are a check runs with given name
        """
        check_runs = self.event.check_runs
        check_run = next(iter(filter(lambda cr: cr.name == name, check_runs)), None)
        assert (
            not check_runs or not check_run
        ), f"There is a Check Run with the name {name}. {[cr.name for cr in check_runs]}"

    def assert_check_run_start(self, name: str, **kwargs) -> None:
        """Asserts that a check run with the given name has been started."""
        check_run = self.get_check_run(name)
        kwargs.setdefault("summary", None)
        kwargs.setdefault("text", None)
        kwargs.setdefault("status", CheckRunStatus.IN_PROGRESS)
        check_run.start.assert_called_once_with(**kwargs)

    def assert_check_run_progression(self, name: str, calls: list[call]) -> None:
        """
        Asserts the progression of check runs for a given name and list of calls.

        :param name: The name of the check run.
        :param calls: The list of calls to be made to the check run.
        :return: None
        :raise AssertionError: If there are no check runs, or if there is no check run with the given name,
         or if there are missing calls.
        """

        def set_defaults(call_: call) -> None:
            """Set default values for the summary and text attributes of the call."""
            for attr in ["summary", "text"]:
                call_.kwargs.setdefault(attr, None)

        check_run = self.get_check_run(name)
        start, *updates = calls
        set_defaults(start)
        check_run.start.assert_called_once_with(*start.args, **start.kwargs)
        mock_calls = check_run.update.mock_calls
        for actual_call, expected_call in zip_longest(mock_calls, updates):
            assert expected_call is not None, "Missing call(s): " + "\n".join(
                str(c) for c in mock_calls[len(updates) :]
            )
            assert actual_call is not None, "Unexpected call(s): " + "\n".join(
                str(c) for c in updates[len(mock_calls) :]
            )
            assert actual_call == expected_call

    def get_check_run(self, name: str) -> EventCheckRun:
        """Get a Check Run by its name."""
        check_runs = self.event.check_runs
        assert check_runs, "There is no Check Runs"
        check_run = next(iter(filter(lambda cr: cr.name == name, check_runs)), None)
        assert check_run, f"There is no Check Run with the name {name}. {[cr.name for cr in check_runs]}"
        return check_run

    def assert_check_run_final_state(
        self,
        name: str,
        title: str = None,
        summary: str = None,
        status: CheckRunStatus = None,
        conclusion: CheckRunConclusion = None,
    ) -> None:
        """
        Asserts that the final state of a check run matches the given parameters.

        :param name: The name of the check run to check.
        :param title: (optional) The expected title of the check run output.
        :param summary: (optional) The expected summary of the check run output.
        :param status: (optional) The expected status of the check run.
        :param conclusion: (optional) The expected conclusion of the check run.
        :return: None
        """
        check_run = self.get_check_run(name)
        github_check_run = check_run._check_run
        if title:
            assert github_check_run.output.title == title
        if summary:
            assert github_check_run.output.summary == summary
        if status:
            assert github_check_run.status == status.value
        if conclusion:
            assert github_check_run.conclusion == conclusion.value

    def deliver(self, event_type: type[Event], **params) -> Optional[Event]:
        """
        This method delivers an event of the specified type with the given parameters.
        It creates an event instance, updates the parameters, and then posts the event to the client.

        The `event_type` parameter defines the type of event to deliver. It should be a subclass of `Event`.

        The `params` parameter is a dictionary containing additional parameters to include in the event.
        If a parameter is not present in `params`, the default value will be used.

        The method uses a patch context to mock certain dependencies and headers for testing purposes.
        If the response status code is not a successful 2XX code, an AssertionError is
        raised with information about the error.
        """

        def update_params(method: type[Event]) -> None:
            """
            This method updates the params dictionary with default values for any missing parameters based on
            the signature of the given method. It also performs attribute name conversions as specified in
             the attribute_name_conversions dictionary. The updated params dictionary is modified in place.
            """
            attribute_name_conversions = {
                "sender": "user",
            }
            for p in inspect.signature(method).parameters:
                if p not in {"gh", "requester", "headers", "kwargs"}:
                    value = self.defaults[attribute_name_conversions.get(p, p)]
                    recursive_update(value, params.get(p, {}))
                    if value.get("owner") == {}:
                        value["owner"] = self.defaults["user"]
                    params[p] = value

        original_event_init = Event.__init__

        def event_init_mock(event_instance: Event, *args, **kwargs) -> None:
            """Just to retrieve the created Event"""
            original_event_init(event_instance, *args, **kwargs)
            self.event = event_instance

        def define_event_identifier(event_type_: type[Event]) -> dict[str, str]:
            """Define the event_identifier for the given event type."""
            event_identifier_ = {}
            if event_type_.event_identifier:
                event_identifier_ = define_event_identifier(event_type_.__base__)
                event_identifier_.update(event_type_.event_identifier)
            update_params(event_type_)
            return event_identifier_

        event_identifier = define_event_identifier(event_type)

        def create_check_run(_, name: str, sha: str, **attributes) -> Mock:
            """Creates a check run object with the given attributes."""
            attributes["name"] = name
            attributes["sha"] = sha
            attributes["url"] = "url"
            mock = self.event._parse_object(CheckRun, attributes)
            return mock

        with (
            patch("githubapp.webhook_handler._get_auth"),
            patch("githubapp.webhook_handler.Github"),
            # To avoid making requests
            patch("githubapp.webhook_handler.Requester") as requester_mock,
            # To return the event to test method
            patch.object(Event, "__init__", event_init_mock),
            # To mock the config file reading
            patch.object(Repository, "get_contents", get_config),
            spy(EventCheckRun),
            # To mock the CheckRun
            patch.object(Repository, "create_check_run", create_check_run),
            # Tu update the mocked CheckRun
            patch.object(CheckRun, "edit", edit),
        ):
            requester_mock().requestJsonAndCheck.return_value = ({}, {})
            headers = {
                "X-Github-Delivery": "19f5cfbe-bc72-48b3-8501-aab458511586",
                "X-GitHub-Event": event_identifier.pop("event"),
                "X-Github-Hook-Id": 111,
                "X-Github-Hook-Installation-Target-Id": 222,
                "X-Github-Hook-Installation-Target-Type": "integration",
            }
            body = {
                "installation": {"id": 123},
            }
            body.update(event_identifier)
            body.update(self.get_info_from_file())
            body.update(params)
            response = self.client.post(
                json=body,
                headers=headers,
            )
            if response.status_code // 100 != 2:
                error = response.json["error"]
                exception_info = error["exception_info"]
                raise AssertionError(
                    f"The response status code is {response.status_code} not 2XX\n"
                    f"{exception_info['type']}({error['message']}) in {exception_info['func']} at "
                    f"{exception_info['filename']}:{exception_info['lineno']}"
                )
            return self.event
