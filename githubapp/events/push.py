from typing import Optional

from github.GitCommit import GitCommit
from github.NamedUser import NamedUser

from githubapp.events.event import Event


class PushEvent(Event):
    """This class represents a push event."""

    event_identifier = {"event": "push"}

    def __init__(
        self,
        after: str,
        base_ref: Optional[str],
        before: str,
        commits: list[dict],
        compare: str,
        created: bool,
        deleted: bool,
        forced: bool,
        head_commit: dict[str, str],
        pusher: dict[str, str],
        ref: str,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.after: str = after
        self.base_ref: Optional[str] = base_ref
        self.before: str = before
        self.commits = [self._parse_object(GitCommit, commit) for commit in commits]
        self.compare: str = compare
        self.created: bool = bool(created)
        self.deleted: bool = bool(deleted)
        self.forced: bool = bool(forced)
        self.head_commit = self._parse_object(GitCommit, head_commit)
        self.pusher = self._parse_object(NamedUser, pusher)
        self.ref: str = ref
