import inspect
import os
import traceback
from collections import defaultdict
from functools import wraps
from importlib.metadata import version as get_version
from typing import Any, Callable, Optional

from github import Consts, Github, GithubIntegration, GithubRetry
from github.AccessToken import AccessToken
from github.Auth import AppAuth, AppUserAuth, Auth, Token
from github.Requester import Requester

from githubapp import Config
from githubapp.events.event import Event


class SignatureError(Exception):
    """Exception when the method has a wrong signature"""

    def __init__(self, method: Callable[[Any], Any], signature: str) -> None:
        """
        Args:
            method (Callable): The method to be validated.
            signature (str): The signature of the method.
        """
        self.message = (
            f"Method {method.__qualname__}({signature}) signature error. "
            f"The method must accept only one argument of the Event type"
        )


handlers = defaultdict(list)


def add_handler(event: type[Event]) -> Callable[[Callable[[Event], None]], Callable]:
    """Decorator to register a method as a webhook handler.

    Args:
      event (type[Event]): The Event subclass to handle.

    Returns:
      Callable: A decorator that validates the handler signature.
    """

    def decorator(handler: Callable[[Event], None]) -> Callable[[Event], None]:
        """Register the method as a handler for the event

        Args:
            handler (Callable): The event handler method to register

        Returns:
            Callable: The registered handler method.
        """
        register_method_for_event(event, handler)
        return handler

    return decorator


def register_method_for_event(event: type[Event], handler: Callable[[Event], None]) -> None:
    """Add a handler for a specific event type.

    The handler must accept only one argument of the Event type.

    Args:
        event (type[Event]): The event type to handle.
        handler (Callable): The handler method.
    """
    if subclasses := event.__subclasses__():
        for sub_event in subclasses:
            register_method_for_event(sub_event, handler)
    else:
        _validate_signature(handler)
        handlers[event].append(handler)


def _get_auth(hook_installation_target_id: int = None, installation_id: int = None) -> Auth:
    """This method is used to get the authentication object for the GitHub API.
    It checks if the environment variables CLIENT_ID, CLIENT_SECRET, and TOKEN are set.
    If they are set, it uses the AppUserAuth object with the CLIENT_ID, CLIENT_SECRET, and TOKEN.
    Otherwise, it uses the AppAuth object with the private key.

    Args:
        hook_installation_target_id (int): The installation target ID.
        installation_id (int): The installation ID.

    Returns:
        Auth: The authentication object.
    """
    if os.environ.get("CLIENT_ID"):
        return AppUserAuth(
            client_id=os.environ.get("CLIENT_ID"),
            client_secret=os.environ.get("CLIENT_SECRET"),
            token=os.environ.get("TOKEN"),
        )
    if not (private_key := os.getenv("PRIVATE_KEY")):
        with open("private-key.pem", "rb") as key_file:  # pragma no cover
            private_key = key_file.read().decode()
    app_auth = AppAuth(hook_installation_target_id, private_key)
    token = GithubIntegration(auth=app_auth).get_access_token(installation_id).token
    return Token(token)


def handle(headers: dict[str, Any], body: dict[str, Any], config_file: str = None) -> None:
    """Handle a webhook request.

    The request headers and body are passed to the appropriate handler methods.

    Args:
        headers (dict): The request headers.
        body (dict): The request body.
        config_file (str): The path to the configuration file.
    """
    event_class = Event.get_event(headers, body)
    hook_installation_target_id = int(headers["X-Github-Hook-Installation-Target-Id"])
    installation_id = int(body["installation"]["id"])

    auth = _get_auth(hook_installation_target_id, installation_id)
    gh = Github(auth=auth)
    requester = Requester(
        auth=auth,
        base_url=Consts.DEFAULT_BASE_URL,
        timeout=Consts.DEFAULT_TIMEOUT,
        user_agent=Consts.DEFAULT_USER_AGENT,
        per_page=Consts.DEFAULT_PER_PAGE,
        verify=True,
        retry=GithubRetry(),
        pool_size=None,
    )
    body.pop("requester", None)

    event = event_class(gh=gh, requester=requester, headers=headers, **body)
    if config_file and event.repository:
        Config.load_config_from_file(config_file, event.repository)
    try:
        for handler in handlers.get(event_class, []):
            handler(event)
    except Exception:
        for cr in event.check_runs:
            if cr.check_run.status != "completed":
                cr.update(conclusion="failure", text=traceback.format_exc())
        raise


def default_index(name, version=None, versions_to_show: Optional[list] = None) -> Callable[[], str]:
    """Decorator to register a default root handler.

    Args:
        name (str): The name of the App.
        version (str): The version of the App.
        versions_to_show (Optional[list]): The libraries to show the version.
    """
    versions_to_show_ = {}
    if version:
        versions_to_show_[name] = version

    for lib in versions_to_show or []:
        versions_to_show_[lib] = get_version(lib)

    def root_wrapper() -> str:
        """A wrapper function to return a default home screen for all Apps

        Returns:
            str: The default home screen.
        """
        resp = f"<h1>{name} App up and running!</h1>"
        if versions_to_show_:
            resp = resp + "\n" + "<br>".join(f"{name_}: {version_}" for name_, version_ in versions_to_show_.items())
        return resp

    return wraps(root_wrapper)(root_wrapper)


def _validate_signature(method: Callable[[Event], None]) -> None:
    """Validate the signature of a webhook handler method.

    The method must accept only one argument of the Event type.

    Args:
        method (Callable[[Event], None]): The method to validate.

    Raises:
        SignatureError: If the method has a wrong signature.
    """
    parameters = inspect.signature(method).parameters
    if len(parameters) != 1:
        signature = ", ".join(parameters.keys())
        raise SignatureError(method, signature)


def handle_with_flask(
    app,
    use_default_index: bool = True,
    webhook_endpoint: str = "/",
    auth_callback_handler: Optional[Callable[[int, AccessToken], None]] = None,
    version: str = None,
    versions_to_show: list[str] = None,
    config_file: str = None,
) -> None:
    """
    This function registers the webhook_handler with a Flask application.

    Args:
        app (Flask): The Flask application to register the webhook_handler with.
        use_default_index (bool): Whether to register the root handler with the Flask application. Default is False.
        webhook_endpoint (str): The endpoint to register the webhook_handler with. Default is "/".
        auth_callback_handler (Callable[[int, AccessToken], None]): The function to handle the auth_callback.
        Default is None.

        version (str): The version of the App.
        versions_to_show (str): The libraries to show the version.
        config_file (str): The config file path to autoload
    Returns:
        None

    Raises:
        TypeError: If the app parameter is not a Flask instance.
    """
    from flask import Flask, request

    if not isinstance(app, Flask):
        raise TypeError("app must be a Flask instance")

    if use_default_index:
        app.route("/", methods=["GET"])(default_index(app.name, version=version, versions_to_show=versions_to_show))

    @app.route(webhook_endpoint, methods=["POST"])
    def webhook() -> str:
        """
        This route is the endpoint that receives the GitHub webhook call.
        It handles the headers and body of the request, and passes them to the webhook_handler for processing.
        """
        headers = dict(request.headers)
        body = request.json
        handle(headers, body, config_file)
        return "OK"

    if auth_callback_handler:
        # methods for:
        # - change the parameter to something like: use-user-oauth
        # - save the access_token @user_oauth_registration
        # - delete on installation.delete event @user_oauth_remove
        # - retrieve access_token @user_oauth_retrieve
        # use @, pass as parameters to this function ou as a class?
        @app.route("/auth-callback")
        def auth_callback() -> str:
            """
            This route is the endpoint that receives the GitHub auth_callback call.
            Call the auth_callback_handler with the installation_id and access_token to be saved.
            """
            args = request.args
            code = args.get("code")
            installation_id = int(args.get("installation_id"))
            access_token = (
                Github()
                .get_oauth_application(os.getenv("CLIENT_ID"), os.getenv("CLIENT_SECRET"))
                .get_access_token(code)
            )

            auth_callback_handler(installation_id, access_token)
            return "OK"
