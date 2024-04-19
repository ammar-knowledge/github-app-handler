from github.GitRelease import GitRelease

from githubapp.events.event import Event


class ReleaseEvent(Event):
    """This class represents a generic release event."""

    event_identifier = {"event": "release"}

    def __init__(self, release: dict[str, str], **kwargs):
        super().__init__(**kwargs)
        self.release = self._parse_object(GitRelease, release)


class ReleaseCreatedEvent(ReleaseEvent):
    """This class represents an event when a release is created."""

    event_identifier = {"action": "created"}


class ReleaseReleasedEvent(ReleaseEvent):
    """This class represents an event when a release is released."""

    event_identifier = {"action": "released"}
