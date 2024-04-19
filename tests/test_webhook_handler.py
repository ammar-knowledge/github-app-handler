from unittest.mock import ANY, Mock, patch

import pytest
from github import GithubIntegration
from github.Auth import AppUserAuth, Token

from githubapp import webhook_handler
from githubapp.webhook_handler import _get_auth, default_index, handle
from tests.mocks import EventTest, SubEventTest


class ExceptionTest(Exception):
    pass


def test_call_handler_sub_event(method, event_action_request):
    """
    Test the call handler sub event.

    Args:
        method: The method to be tested.
        event_action_request: The event action request.

    Raises:
        AssertionError: If the assertions fail.

    Example:
        test_call_handler_sub_event(method, event_action_request)
    """
    assert webhook_handler.add_handler(SubEventTest)(method) == method

    assert len(webhook_handler.handlers) == 1
    assert webhook_handler.handlers.get(SubEventTest) == [method]


def test_get_auth_app_user_auth(monkeypatch):
    monkeypatch.setenv("CLIENT_ID", "client_id")
    monkeypatch.setenv("CLIENT_SECRET", "client_secret")
    monkeypatch.setenv("TOKEN", "token")
    with patch("githubapp.webhook_handler.AppUserAuth", autospec=AppUserAuth) as appuserauth:
        assert isinstance(_get_auth(), AppUserAuth)
        appuserauth.assert_called_once_with(client_id="client_id", client_secret="client_secret", token="token")


def test_get_auth_app_auth_when_private_key_in_env(monkeypatch):
    monkeypatch.setenv("PRIVATE_KEY", "private_key")

    get_access_token = Mock(return_value=Mock(token="token"))
    githubintegration = Mock(autospec=GithubIntegration, get_access_token=get_access_token)
    with (
        patch("githubapp.webhook_handler.AppAuth") as appauth,
        patch(
            "githubapp.webhook_handler.GithubIntegration",
            return_value=githubintegration,
            autospec=GithubIntegration,
        ) as GithubIntegrationMock,
        patch("githubapp.webhook_handler.Token", autospec=Token) as TokenMock,
    ):
        assert isinstance(_get_auth(123456, 654321), Token)
        appauth.assert_called_once_with(123456, "private_key")
        GithubIntegrationMock.assert_called_once_with(auth=appauth.return_value)
        get_access_token.assert_called_once_with(654321)
        TokenMock.assert_called_once_with("token")


def test_default_index():
    wrapper = default_index("name")
    assert wrapper() == "<h1>name App up and running!</h1>"


def test_default_index_show_version():
    wrapper = default_index("name", version="1.0")
    assert (
        wrapper()
        == """<h1>name App up and running!</h1>
name: 1.0"""
    )


def test_default_index_show_libraries_versions():
    with patch("githubapp.webhook_handler.get_version", return_value="2.0"):
        wrapper = default_index("name", "1.0", ["pygithub"])
    assert (
        wrapper()
        == """<h1>name App up and running!</h1>
name: 1.0<br>pygithub: 2.0"""
    )


def test_when_exception_and_has_check_run(event, event_action_request, mock_auth):
    def method(inner_event):
        inner_event.repository = event.repository
        inner_event.start_check_run("name", "sha", title="title")
        event.check_runs = inner_event.check_runs
        raise ExceptionTest("test")

    webhook_handler.register_method_for_event(EventTest, method)
    with pytest.raises(ExceptionTest):
        handle(*event_action_request)

    assert len(event.check_runs) == 1
    check_run = event.check_runs[0].check_run
    check_run.edit.assert_called_with(
        conclusion="failure",
        status="completed",
        output={"title": ANY, "summary": ANY, "text": ANY},
    )
    output_text = check_run.edit.call_args_list[0].kwargs["output"]["text"]
    assert output_text.startswith("Traceback (most recent call last):")
    assert output_text.endswith("ExceptionTest: test\n")


def test_when_exception_and_dont_has_check_run(event, event_action_request, mock_auth):
    def method(inner_event):
        inner_event.repository = event.repository
        event.check_runs = inner_event.check_runs
        raise ExceptionTest("test")

    webhook_handler.register_method_for_event(EventTest, method)
    with pytest.raises(ExceptionTest):
        handle(*event_action_request)

    assert event.check_runs == []
