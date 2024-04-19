from github.Issue import Issue
from github.IssueComment import IssueComment

from githubapp.events.event import Event


class IssueCommentEvent(Event):
    """This class represents a generic issue comment event."""

    event_identifier = {"event": "issue_comment"}

    def __init__(self, issue: dict[str, str], issue_comment: dict[str, str], **kwargs):
        super().__init__(**kwargs)
        self.issue = self._parse_object(Issue, issue)
        self.issue_comment = self._parse_object(IssueComment, issue_comment)


class IssueCommentCreatedEvent(IssueCommentEvent):
    """This class represents an event when a comment in an Issue is created."""

    event_identifier = {"action": "created"}


class IssueCommentEditedEvent(IssueCommentEvent):
    """This class represents an event when a comment in an Issue is edited."""

    event_identifier = {"action": "edited"}

    def __init__(self, changes: dict[str, str], **kwargs):
        super().__init__(**kwargs)
        self.changes = changes


class IssueCommentDeletedEvent(IssueCommentEvent):
    """This class represents an event when a comment in an Issue is deleted."""

    event_identifier = {"action": "deleted"}
