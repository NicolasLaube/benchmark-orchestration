"""
This module contains custom exceptions for the InferenceClient.
"""


class InferenceClientError(Exception):
    """Base error raised when the orchestrator cannot get a valid inference response."""


class InferenceRateLimitedError(InferenceClientError):
    """Raised when the inference service returns HTTP 429."""

    def __init__(
        self,
        retry_after_sec: int,
        message: str,
        reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after_sec = retry_after_sec
        self.reason = reason


class InferenceHttpError(InferenceClientError):
    """Raised when the inference service returns a non-2xx HTTP response."""


class InferenceNetworkError(InferenceClientError):
    """Raised when the inference service cannot be reached or times out."""
