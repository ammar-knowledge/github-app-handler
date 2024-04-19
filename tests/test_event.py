from unittest.mock import Mock

from githubapp.events.event import Event
from tests.conftest import event_action_request
from tests.mocks import EventTest, SubEventTest


# noinspection PyUnresolvedReferences
def test_init(event_action_request):
    headers, body = event_action_request
    SubEventTest(gh=Mock(), requester=Mock(), headers=headers, **body)
    assert Event.github_event == "event"
    assert Event.hook_id == 1
    assert Event.delivery == "a1b2c3d4"
    assert Event.hook_installation_target_type == "type"
    assert Event.hook_installation_target_id == 2


def test_normalize_dicts():
    d1 = {"a": "1"}
    d2 = {"X-Github-batata": "Batata"}

    union_dict = Event.normalize_dicts(d1, d2)
    assert union_dict == {"a": "1", "batata": "Batata"}


def test_get_event(event_action_request):
    headers, body = event_action_request
    assert Event.get_event(headers, body) == SubEventTest
    body.pop("action")
    assert Event.get_event(headers, body) == EventTest


def test_match():
    d1 = {"a": 1, "b": 2}
    d2 = {"b": 2}
    d3 = {"a": 1, "b": 1}

    class LocalEventTest(Event):
        pass

    LocalEventTest.event_identifier = d2
    assert LocalEventTest.match(d1) is True
    assert LocalEventTest.match(d3) is False
    LocalEventTest.event_identifier = d1
    assert LocalEventTest.match(d3) is False


def test_lazy_fix_url():
    attributes = {"url": "https://github.com/potato"}
    Event.fix_attributes(attributes)
    assert attributes["url"] == "https://api.github.com/repos/potato"


def test_lazy_fix_url_when_is_correct():
    attributes = {"url": "correct_url"}
    Event.fix_attributes(attributes)
    assert attributes["url"] == "correct_url"


# noinspection PyTypeChecker
def test_parse_object():
    mocked_class = Mock()
    self = Mock(requester="requester")
    EventTest._parse_object(self, mocked_class, {"a": 1})
    self.fix_attributes.assert_called_with({"a": 1})
    mocked_class.assert_called_with(requester="requester", headers={}, attributes={"a": 1}, completed=False)


# noinspection PyTypeChecker
def test_parse_object_when_value_is_none():
    mocked_class = Mock()
    self = Mock(requester="requester")
    EventTest._parse_object(self, mocked_class, None)
    self.fix_attributes.assert_not_called()
    mocked_class.assert_not_called()
