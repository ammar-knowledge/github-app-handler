from githubapp.events.event import Event


class CreateEvent(Event):
    """This class represents a branch or tag creation event."""

    event_identifier = {"event": "create"}

    def __init__(
        self,
        description: str,
        master_branch: str,
        pusher_type: str,
        ref: str,
        ref_type: str,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.description = description
        self.master_branch = master_branch
        self.pusher_type = pusher_type
        self.ref = ref
        self.ref_type = ref_type


class CreateBranchEvent(CreateEvent):
    """This class represents a branch creation event."""

    event_identifier = {"ref_type": "branch"}


class CreateTagEvent(CreateEvent):
    """This class represents a tag creation event."""

    event_identifier = {"ref_type": "tag"}
