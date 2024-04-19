"""
Module for handling GitHub check_suite webhook events.
https://docs.github.com/en/webhooks/webhook-events-and-payloads#check_suite
"""

from github.CheckSuite import CheckSuite

from githubapp.events.event import Event


class CheckSuiteEvent(Event):
    """This class represents an check suite event."""

    event_identifier = {"event": "check_suite"}

    def __init__(
        self,
        check_suite: dict[str, str],
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.check_suite = self._parse_object(CheckSuite, check_suite)


class CheckSuiteRequestedEvent(CheckSuiteEvent):
    """This class represents an check suite requested event."""

    event_identifier = {"action": "requested"}


class CheckSuiteCompletedEvent(CheckSuiteEvent):
    """This class represents an check suite completed event."""

    event_identifier = {"action": "completed"}


class CheckSuiteRerequestedEvent(CheckSuiteEvent):
    """This class represents an check suite rerequested event."""

    event_identifier = {"action": "rerequested"}
