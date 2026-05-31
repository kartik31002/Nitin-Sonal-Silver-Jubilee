"""Shared logging setup using Rich."""

from __future__ import annotations

import logging

from rich.console import Console
from rich.logging import RichHandler

_console = Console()


def get_console() -> Console:
    return _console


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handler = RichHandler(
        console=_console,
        show_time=False,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[handler],
        force=True,
    )

    for noisy in (
        "googleapiclient",
        "googleapiclient.http",
        "googleapiclient.discovery",
        "google_auth_httplib2",
        "google.auth.transport",
        "urllib3",
        "urllib3.connectionpool",
        "PIL",
        "requests",
    ):
        logging.getLogger(noisy).setLevel(logging.ERROR)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
