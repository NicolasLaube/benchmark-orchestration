"""
This module defines the `AttemptOutcome` dataclass, which represents the outcome of an attempt to
answer a benchmark question. It includes information about the question, the attempt number,
the result of the attempt, any errors encountered, and metrics related to rate limiting and observed
performance.
"""

from dataclasses import dataclass

from orchestrator.domain.models.question import BenchmarkQuestion
from orchestrator.domain.models.question_result import QuestionResult


@dataclass(slots=True)
class AttemptOutcome:
    """
    Represents the outcome of an attempt to answer a benchmark question.

    Attributes:
        question (BenchmarkQuestion): The benchmark question being attempted.
        attempt (int): The attempt number.
        result (QuestionResult | None): The result of the attempt, if available.
        error (str | None): Any error encountered during the attempt.
        error_type (str | None): The type of error encountered, if any.
        retry_after_sec (int | None): The number of seconds to wait before retrying, if rate
        limited.
        rate_limit_reason (str | None): The reason for rate limiting, if applicable.
        observed_launch_rpm (int): The observed launch rate per minute at the time of the attempt.
        observed_in_flight (int): The number of in-flight requests at the time of the attempt.
    """

    question: BenchmarkQuestion
    attempt: int
    result: QuestionResult | None = None  # type: ignore
    error: str | None = None
    error_type: str | None = None
    retry_after_sec: int | None = None
    rate_limit_reason: str | None = None
    observed_launch_rpm: int = 0
    observed_in_flight: int = 0


@dataclass(slots=True)
class ControlUpdate:
    """
    Represents a control update event in the scheduler, capturing the state of the scheduler before
    and after the update.

    Attributes:
        cause (str): The cause of the control update.
        old_concurrency (int): The concurrency level before the update.
        old_interval (float): The launch interval before the update.
        old_phase (str): The phase of the scheduler before the update.
        event (str): The type of event, defaulting to "CONTROL_UPDATE".


    """

    cause: str
    old_concurrency: int
    old_interval: float
    old_phase: str
    event: str = "CONTROL_UPDATE"
