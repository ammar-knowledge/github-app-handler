from collections import defaultdict
from unittest.mock import Mock, patch

import pytest
from github.Auth import Auth

from githubapp import webhook_handler
from githubapp.events.event import Event


@pytest.fixture(autouse=True)
def gh():
    """mock the requests library for tests"""
    with patch("githubapp.webhook_handler.Github"):
        yield


@pytest.fixture(autouse=True)
def requester():
    """mock the requests library for tests"""
    with patch("githubapp.webhook_handler.Requester"):
        yield


@pytest.fixture
def mock_auth():
    with patch("githubapp.webhook_handler._get_auth", return_value=Mock(autospec=Auth)) as mock:
        yield mock


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """setup and teardown for tests"""
    yield
    webhook_handler.handlers = defaultdict(list)


@pytest.fixture
def event_action_request():
    """Commons headers and body for tests"""
    headers = {
        "X-Github-Event": "event",
        "X-Github-Hook-Id": "1",
        "X-Github-Delivery": "a1b2c3d4",
        "X-Github-Hook-Installation-Target-Type": "type",
        "X-Github-Hook-Installation-Target-Id": "2",
    }
    body = {
        "installation": {"id": "3"},
        "action": "action",
        "sender": {},
        "repository": {},
    }
    yield headers, body


@pytest.fixture
def method():
    """returns a mock for the dummy method for tests"""

    def dummy(event):
        """A dummy method for tests"""
        return event

    yield Mock(wraps=dummy)


@pytest.fixture(autouse=True)
def validate_signature():
    """mock the _validate_signature method to allways return true"""
    with patch(
        "githubapp.webhook_handler._validate_signature",
        return_value=True,
    ):
        yield


@pytest.fixture
def event(event_action_request):
    headers, _ = event_action_request
    event = Event(
        gh=Mock(),
        requester=Mock(),
        headers=headers,
        sender=None,
        repository={},
    )
    event.repository = Mock()
    return event
