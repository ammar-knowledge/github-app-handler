from typing import Optional

from github.Branch import Branch
from github.Commit import Commit

from githubapp.events.event import Event


class StatusEvent(Event):
    """This class represents a status report."""

    event_identifier = {"event": "status"}

    def __init__(
        self,
        branches: list[dict],
        commit: dict[str, str],
        context: str,
        created_at: str,
        description: Optional[str],
        id: int,
        name: str,
        sha: str,
        state: str,
        target_url: Optional[str],
        updated_at: str,
        **kwargs,
    ):
        """
        Initialize a new instance of the class.

        Args:
            headers: The headers for the instance.
            branches: The list of branches.
            commit: The Git commit instance.
            context: The context of the instance.
            created_at: The creation date of the instance.
            description: The description of the instance.
            id: The ID of the instance.
            name: The name of the instance.
            repository: The repository instance.
            sender: The sender of the instance.
            sha: The SHA of the instance.
            state: The state of the instance.
            target_url: The target URL of the instance.
            updated_at: The update date of the instance.
            **kwargs: Additional keyword arguments.

        Raises:
            Any exceptions that may occur during initialization.

        """
        super().__init__(**kwargs)
        self.branches = [self._parse_object(Branch, branch) for branch in branches]
        self.commit = self._parse_object(Commit, commit)
        self.context: str = context
        self.created_at: str = created_at
        self.description: Optional[str] = description
        self.id: int = id
        self.name: str = name

        self.sha: str = sha
        self.state: str = state
        self.target_url: Optional[str] = target_url
        self.updated_at: str = updated_at
