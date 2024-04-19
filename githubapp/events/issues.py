from github.Issue import Issue
from github.Repository import Repository

from githubapp.events.event import Event


class IssuesEvent(Event):
    """This class represents an issue event."""

    event_identifier = {"event": "issues"}

    def __init__(
        self,
        issue: dict[str, str],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.issue = self._parse_object(Issue, issue)


class IssueOpenedEvent(IssuesEvent):
    """This class represents an issue opened event."""

    event_identifier = {"action": "opened"}

    def __init__(
        self,
        changes: dict[str, str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.old_issue = self._parse_object(Issue, changes.get("old_issue")) if changes else None
        self.old_repository = self._parse_object(Repository, changes.get("old_repository")) if changes else None


class IssueEditedEvent(IssuesEvent):
    """This class represents an issue edited event."""

    event_identifier = {"action": "edited"}

    def __init__(
        self,
        changes: dict[str, str],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.changes = changes


class IssueClosedEvent(IssuesEvent):
    """This class represents an issue closed event."""

    event_identifier = {"action": "closed"}
