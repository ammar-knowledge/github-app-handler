"""
This module initializes the githubapp module and sets the version number for the module.

It is the entry point for the githubapp package and is responsible for initializing all
the necessary components and configurations. Any global settings for the package should be defined here.
"""

from githubapp.config import Config
from githubapp.event_check_run import EventCheckRun

__version__ = "0.27.2"

__all__ = ["Config", "EventCheckRun"]
