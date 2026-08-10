import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Protocol, Self

from orchestrator.monitoring.run_metrics import RunMetrics


class EventLogger(Protocol):
    def __call__(
        self,
        logger: logging.Logger,
        level: int,
        event: str,
        **fields: object,
    ) -> None: ...


class ProgressView(Protocol):
    def __enter__(self) -> Self: ...
    def __exit__(self, exc_type, exc, tb) -> None: ...
    def refresh(self) -> None: ...
    def final_summary(self) -> object: ...


ProgressViewFactory = Callable[
    [RunMetrics],
    AbstractContextManager[ProgressView],
]
