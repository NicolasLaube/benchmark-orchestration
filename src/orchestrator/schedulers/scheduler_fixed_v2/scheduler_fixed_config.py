"""
This module defines the `FixedConcurrencyConfig` data class, which represents the configuration
for a fixed concurrency scheduler. It includes parameters such as maximum concurrency, maximum
retries, maximum backoff time, and progress logging frequency. The class also includes validation
logic in the `__post_init__` method to ensure that the configuration values are within acceptable
ranges.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FixedConcurrencyConfig:
    """Represents the configuration for a fixed concurrency scheduler."""

    max_concurrency: int = 4
    # The maximum number of concurrent requests that the scheduler can handle.
    max_retries: int = 3
    # The maximum number of retries for a failed request before giving up.
    max_backoff_sec: float = 8.0
    # The maximum backoff time in seconds for retrying failed requests.

    # None when Rich already displays continuous progress.
    # Set to 10 to reproduce the previous periodic logs.
    progress_log_every: int | None = None

    def __post_init__(self) -> None:
        if self.max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than 0")

        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")

        if self.max_backoff_sec <= 0:
            raise ValueError("max_backoff_sec must be > 0")

        if self.progress_log_every is not None and self.progress_log_every <= 0:
            raise ValueError("progress_log_every must be > 0 or None")
