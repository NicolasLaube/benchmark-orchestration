"""
This module provides a utility function for logging events with structured fields using Python's
built-in logging module.
The `log_event` function allows for logging events at a specified logging level, along with
additional key-value pairs that provide context for the event. The fields are formatted into a
single string and included in the log message, making it easier to analyze logs and understand
the context of events.
"""

import logging
from typing import Any


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    **fields: Any,
) -> None:
    """Logs an event with the specified level and fields."""
    formatted_fields = " | ".join(
        f"{key}={value}" for key, value in fields.items() if value is not None
    )

    message = event

    if formatted_fields:
        message = f"{event} | {formatted_fields}"

    logger.log(level, message)
