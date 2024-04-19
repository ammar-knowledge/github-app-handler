from unittest.mock import Mock

import pytest
from github import UnknownObjectException

from githubapp import Config
from githubapp.config import ConfigError

CONFIG_TEST = """
config1: value1

config2:
    subconfig1: value2
    
config3:
    - value3
    - value4
"""


@pytest.fixture(autouse=True)
def clear_config():
    for attr in vars(Config).copy().keys():
        delattr(Config, attr)
    yield


def test_config():
    repository = Mock()
    repository.get_contents.return_value = Mock(decoded_content=CONFIG_TEST)
    Config.load_config_from_file("file", repository)

    assert Config.config1 == "value1"
    assert Config.config2.subconfig1 == "value2"
    assert Config.config3 == ["value3", "value4"]


def test_default_values():
    repository = Mock()
    repository.get_contents.return_value = Mock(
        decoded_content="""
feature3: override_value
"""
    )
    Config.create_config("feature1", default="default1")
    Config.create_config("feature2", subfeature1="default2")
    Config.load_config_from_file("file", repository)

    assert Config.feature1 == "default1"
    assert Config.feature2.subfeature1 == "default2"
    assert Config.feature3 == "override_value"


def test_config_on_file_not_found():
    repository = Mock()
    repository.get_contents.side_effect = UnknownObjectException(404)
    Config.load_config_from_file("file", repository)
    Config.create_config("config1", default="default1")

    assert Config.config1 == "default1"


def test_no_config_value():
    repository = Mock()
    repository.get_contents.return_value = Mock(decoded_content="")
    Config.load_config_from_file("file", repository)

    with pytest.raises(ConfigError) as err:
        # noinspection PyStatementEffect
        Config.config1
    assert str(err.value) == "No such config value: config1. And there is no default value for it"


def test_validate_default_or_values():
    with pytest.raises(ConfigError) as err:
        Config.create_config("config1", default="value1", value2="value2")
    assert str(err.value) == "You cannot set the default value AND default values for sub values"


def test_config_call_if_call():
    Config.create_config("config", enabled=True)
    called = False

    @Config.call_if("config.enabled")
    def call():
        nonlocal called
        called = True
        return "value"

    call.called = lambda: called

    assert call() == "value"
    assert call.called()


def test_config_call_if_dont_call():
    Config.create_config("config", enabled=False)
    called = False

    @Config.call_if("config.enabled")
    def call():
        nonlocal called
        called = True
        return "value"

    call.called = lambda: called

    assert call() is None
    assert call.called() is False


def test_config_call_if_dont_call_with_default_return_value():
    Config.create_config("config", enabled=False)
    called = False

    @Config.call_if("config.enabled", return_on_not_call="returned_value")
    def call():
        nonlocal called
        called = True
        return "value"

    call.called = lambda: called

    assert call() == "returned_value"
    assert call.called() is False


def test_config_call_if_call_compare_with_value():
    Config.create_config("config", inner={"value": "value"})
    called = False

    @Config.call_if("config.inner.value", "value")
    def call():
        nonlocal called
        called = True

    call.called = lambda: called

    call()
    assert call.called()


def test_config_call_if_dont_call_compare_with_value():
    Config.create_config("config", value="value")
    called = False

    @Config.call_if("config.value", "other_value")
    def call():
        nonlocal called
        called = True

    call.called = lambda: called

    call()
    assert call.called() is False


def test_config_call_if_with_env(monkeypatch):
    monkeypatch.setenv("SHOULD_CALL", "YES")
    called = False

    @Config.call_if("SHOULD_CALL")
    def call():
        nonlocal called
        called = True

    call.called = lambda: called

    call()
    assert call.called() is True
