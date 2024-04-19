import inspect
import os
from typing import Union
from unittest import TestCase
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from flask import Flask

from githubapp import webhook_handler
from githubapp.events.event import Event
from githubapp.webhook_handler import handle_with_flask


def _get_events(main_event=Event, event_identifier=None) -> list[type[Event]]:
    if main_event.__name__.endswith("Test"):
        return []
    events = []
    event_identifier = event_identifier or {}
    event_identifier.update(main_event.event_identifier or {})
    for sub_event in main_event.__subclasses__():
        sub_event.event_identifier.update(event_identifier)
        if sub_event.__subclasses__():
            events.extend(_get_events(sub_event, event_identifier.copy()))
        else:
            events.append(sub_event)
    return events


def _get_parameters(event):
    parameters = dict(inspect.signature(event).parameters)
    if event.__base__ != Event:
        parameters.update(_get_parameters(event.__base__))
    return parameters.items()


@pytest.fixture
def app():
    mock = MagicMock(spec=Flask)()
    mock.__class__ = Flask
    return mock


def _generate_default(type_):
    if args := getattr(type_, "__args__", None):
        origin = type_.__origin__
        if origin is Union:
            return args[0]()
        if origin is list:
            return [_generate_default(args[0])]
    return type_()


@pytest.fixture
def client():
    app = Flask("Test")
    handle_with_flask(app)
    yield app.test_client()


def test_handle_with_flask(app):
    handle_with_flask(app)
    assert app.route.call_count == 2
    app.route.assert_has_calls([call("/", methods=["GET"]), call("/", methods=["POST"])], any_order=True)


def test_handle_with_flask_validation(app):
    class Other:
        pass

    app.__class__ = Other
    with pytest.raises(TypeError):
        handle_with_flask(app)
    assert app.route.call_count == 0


class TestCaseAppHandler(TestCase):
    def setUp(self):
        app = Flask("Test")
        handle_with_flask(app)
        self.app = app
        self.client = app.test_client()

    def test_root(self):
        """
        Test the root endpoint of the application.
        This test ensures that the root endpoint ("/") of the application is working correctly.
        It sends a GET request to the root endpoint and checks that the response status code is 200 and the response
        text is "Pull Request Generator App up and running!".
        """
        response = self.client.get("/")
        assert response.status_code == 200
        assert response.text == "<h1>Test App up and running!</h1>"

    @staticmethod
    def test_root_not_default_index():
        app = Flask("Test")
        handle_with_flask(app, use_default_index=False)
        app.route("/", methods=["GET"])(lambda: "index")
        response = app.test_client().get("/")
        assert response.status_code == 200
        assert response.text == "index"

    @staticmethod
    def test_auth_callback():
        auth_callback = Mock()
        app = Flask("Test")
        handle_with_flask(app, auth_callback_handler=auth_callback)
        os.environ["CLIENT_ID"] = "id"
        os.environ["CLIENT_SECRET"] = "secret"
        with patch("githubapp.webhook_handler.Github") as gh:
            response = app.test_client().get(
                "/auth-callback?code=user_code&installation_id=123456&setup_action=install"
            )

        get_oauth_application = gh.return_value.get_oauth_application
        get_oauth_application.assert_called_once_with("id", "secret")
        get_access_token = get_oauth_application.return_value.get_access_token
        get_access_token.assert_called_once_with("user_code")

        assert response.status_code == 200
        auth_callback.assert_called_with(123456, get_access_token.return_value)

    def test_webhook(self):
        """
        Test the webhook handler of the application.
        This test ensures that the webhook handler is working correctly.
        It mocks the `handle` function of the `webhook_handler` module, sends a POST request to the root endpoint ("/")
        with a specific JSON payload and headers, and checks that the `handle` function is called with the correct
        arguments.
        """
        with patch("githubapp.webhook_handler.handle") as mock_handle:
            request_json = {"action": "opened", "number": 1}
            headers = {
                "User-Agent": "Werkzeug/3.0.1",
                "Host": "localhost",
                "Content-Type": "application/json",
                "Content-Length": "33",
                "X-Github-Event": "pull_request",
            }
            self.client.post("/", headers=headers, json=request_json)
            mock_handle.assert_called_once_with(headers, request_json, None)

    def send_event(self, event):
        event_identifier = event.event_identifier.copy()
        headers = {
            "Content-Type": "application/json",
            "X-Github-Event": event_identifier.pop("event"),
            "X-Github-Hook-Installation-Target-Id": 1,
            "X-Github-Hook-Installation-Target-Type": "integration",
            "X-Github-Delivery": "36adea52-3cd6-4726-a03a-4d8eebcb7364",
            "X-Github-Hook-Id": 3,
        }
        body = {"installation": {"id": 2}, "sender": {}}
        for name, parameter in _get_parameters(event):
            if name == "kwargs":
                continue
            body[name] = _generate_default(parameter.annotation)
        body.update(event_identifier)
        return self.client.post("/", headers=headers, json=body)


@pytest.fixture(autouse=True)
def set_up(monkeypatch):
    monkeypatch.setenv("PRIVATE_KEY", "private_key")
    with (
        patch("githubapp.webhook_handler.GithubIntegration"),
        patch("githubapp.webhook_handler.AppUserAuth"),
        patch("githubapp.webhook_handler.Token"),
    ):
        yield


@pytest.mark.parametrize("event", _get_events())
def test_webhook(event: type[Event], client):
    called = False

    @webhook_handler.add_handler(event)
    def handler(event_handled: Event):
        nonlocal called
        called = True
        assert isinstance(event_handled, event)

    handler.called = lambda: called

    response = TestCaseAppHandler.send_event(Mock(client=client), event)

    assert response.status_code == 200
    assert handler.called()
