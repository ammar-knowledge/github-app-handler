import re
from typing import Any, Optional, TypeVar

from github.NamedUser import NamedUser
from github.Repository import Repository

from githubapp import EventCheckRun

T = TypeVar("T")


class Event:
    """Event base class

    This class represents a generic GitHub webhook event.
    It provides common
    attributes and methods for parsing event data from the request headers and body.
    """

    delivery = None
    github_event = None
    hook_id = None
    hook_installation_target_id = None
    hook_installation_target_type = None
    installation_id = None
    event_identifier = None

    _raw_body = None
    _raw_headers = None

    #
    def __init__(self, *, gh, requester, headers, sender, repository=None, **kwargs):
        Event.delivery = headers["X-Github-Delivery"]
        Event.github_event = headers["X-Github-Event"]
        Event.hook_id = int(headers["X-Github-Hook-Id"])
        Event.hook_installation_target_id = int(headers["X-Github-Hook-Installation-Target-Id"])
        Event.hook_installation_target_type = headers["X-Github-Hook-Installation-Target-Type"]
        if installation_id := kwargs.get("installation", {}).get("id"):
            installation_id = int(installation_id)
        Event.installation_id = installation_id
        Event._raw_headers = headers
        Event._raw_body = kwargs
        self.gh = gh
        self.requester = requester
        self.repository = self._parse_object(Repository, repository)
        self.sender = self._parse_object(NamedUser, sender)
        self.check_runs: list[EventCheckRun] = []

    @staticmethod
    def normalize_dicts(*dicts) -> dict[str, str]:
        """Normalize the event data to a common format

        Args:
            *dicts: A list of dicts containing the event data

        Returns:
            dict: A dict containing the normalized event data
        """
        union_dict = {}
        for d in dicts:
            for attr, value in d.items():
                attr = attr.lower()
                attr = attr.replace("x-github-", "")
                attr = re.sub(r"[- ]", "_", attr)
                union_dict[attr] = value

        return union_dict

    @classmethod
    def get_event(cls, headers, body) -> type["Event"]:
        """Get the event class based on the event type

        Args:
            headers (dict): The request headers
            body (dict): The request body

        Returns:
            Event: The event class
        """
        event_class = cls
        union_dict = Event.normalize_dicts(headers, body)

        for event in cls.__subclasses__():
            if event.match(union_dict):
                return event.get_event(headers, body)
        return event_class

    @classmethod
    def match(cls, data):
        """Check if the event matches the event_identifier

        Args:
            data: A dict containing all the event data

        Returns:
            bool: True if the event matches the event_identifier, False otherwise
        """
        return all((attr in data and value == data[attr]) for attr, value in cls.event_identifier.items())

    @staticmethod
    def fix_attributes(attributes):
        """Fix the url value"""
        if attributes.get("url", "").startswith("https://github"):
            attributes["url"] = (
                attributes["url"]
                .replace("https://github.com", "https://api.github.com/repos")
                .replace("/commit/", "/commits/")
            )

    def _parse_object(self, clazz: type[T], value: Any) -> Optional[T]:
        """Return the PyGithub object"""
        if value is None:
            return None
        self.fix_attributes(value)
        return clazz(
            requester=self.requester,
            headers={},
            attributes=value,
            completed=False,
        )

    def start_check_run(
        self,
        name: str,
        sha: str,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        text: Optional[str] = None,
        status: str = "in_progress",
    ):
        """Start a check run"""
        event_check_run = EventCheckRun(self.repository, name, sha)
        event_check_run.start(title=title, summary=summary, text=text, status=status)
        self.check_runs.append(event_check_run)
        return event_check_run
