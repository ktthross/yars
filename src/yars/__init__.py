"""
YARS (Yet Another Reddit Scraper)

A Python package for scraping Reddit posts, comments, user data, and media.
"""

from .yars import YARS
from .sessions import RandomUserAgentSession
from .utils import display_results, download_image, download_video, export_to_json, export_to_csv
from .agents import get_agent

try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    from importlib_metadata import version, PackageNotFoundError  # type: ignore

try:
    __version__ = version("yars")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = [
    "YARS",
    "RandomUserAgentSession", 
    "display_results",
    "download_image",
    "download_video",
    "export_to_json",
    "export_to_csv",
    "get_agent",
]