"""
This module provides a function to configure logging for the orchestrator application.
The `configure_logging` function sets up the logging configuration, including the log level,
log format, and handlers. It uses the Rich library to provide enhanced logging output in the console
with rich tracebacks and formatting.
The function also sets the log level for the `httpx` library to WARNING to reduce verbosity in the
 logs.
"""

import logging

import typer
from rich.console import Console
from rich.logging import RichHandler


def configure_logging(
    log_level: str,
    console: Console,
) -> logging.Logger:
    level = getattr(
        logging,
        log_level.upper(),
        None,
    )

    if not isinstance(level, int):
        raise typer.BadParameter(f"Invalid log level: {log_level}")

    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                show_time=True,
                show_level=True,
                show_path=False,
            )
        ],
        force=True,
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)

    return logging.getLogger("orchestrator.scheduler")
