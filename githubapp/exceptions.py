"""Github App Exceptions"""


class GithubAppRuntimeException(Exception):
    """An exception that will not be reraised at the end of the webhook_handler.handle call"""
