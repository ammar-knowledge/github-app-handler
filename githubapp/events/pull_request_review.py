from github.PullRequest import PullRequest
from github.PullRequestReview import PullRequestReview

from githubapp.events.event import Event


class PullRequestReviewEvent(Event):
    """This class represents a pull request review event."""

    event_identifier = {"event": "pull_request_review"}

    def __init__(
        self,
        pull_request: dict[str, str],
        review: dict[str, str],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.pull_request = self._parse_object(PullRequest, pull_request)
        self.review = self._parse_object(PullRequestReview, review)


class PullRequestReviewSubmittedEvent(PullRequestReviewEvent):
    """This class represents a pull request review submitted event."""

    event_identifier = {"action": "submitted"}


class PullRequestReviewEditedEvent(PullRequestReviewEvent):
    """This class represents a pull request review edited event."""

    event_identifier = {"action": "edited"}

    def __init__(self, changes: dict[str, str], **kwargs):
        super().__init__(**kwargs)
        self.changes = changes


class PullRequestReviewDismissedEvent(PullRequestReviewEvent):
    """This class represents a pull request review dismissed event."""

    event_identifier = {"action": "dismissed"}
