"""
SchedulerRuntime provides shared functionality for executing HTTP requests, handling pauses,
retries, and observability in a benchmarking context. It manages the lifecycle of benchmark question
 attempts, including dispatching requests, grading responses, and recording metrics.
"""

import asyncio
import logging
import random
import time
from contextlib import nullcontext

from orchestrator.grader.substring import SubstringGrader
from orchestrator.inference_client.client import (
    InferenceClient,
    InferenceClientError,
    InferenceRateLimitedError,
)
from orchestrator.loaders.models import BenchmarkQuestion
from orchestrator.monitoring.logger_logging.log_event import log_event
from orchestrator.monitoring.logger_rich.rich_progress_view import (
    RichProgressView,
)
from orchestrator.report.models import QuestionResult
from orchestrator.schedulers.common.metrics import SchedulerMetrics
from orchestrator.schedulers.common.models import AttemptOutcome
from orchestrator.schedulers.common.types import (
    EventLogger,
    ProgressView,
    ProgressViewFactory,
)
from rich.console import Console


class SchedulerRuntime:
    """Shared HTTP execution, pause handling, retries and observability."""

    def __init__(
        self,
        inference_client: InferenceClient,
        grader: SubstringGrader,
        *,
        logger: logging.Logger | None = None,
        event_logger: EventLogger = log_event,
        console: Console | None = None,
        progress_view_factory: ProgressViewFactory | None = RichProgressView,
    ) -> None:
        # SchedulerRuntime is initialized with an inference client, a grader, and optional logging
        # and console parameters.
        self.inference_client = inference_client
        self.grader = grader
        self.logger = logger or logging.getLogger(__name__)
        self.event_logger = event_logger
        self.console = console or Console()
        self.progress_view_factory = progress_view_factory

        # Metrics state (RunMetrics) is managed by SchedulerMetrics, which handles concurrency
        # and locking.
        self.metrics_state = SchedulerMetrics()

        # Pause handling state
        # The pause_until timestamp indicates when the scheduler can resume processing after
        # a global
        # pause (e.g., due to rate limiting). The pause_lock ensures that updates to this timestamp
        # are thread-safe.
        self.pause_until = 0.0
        self.pause_lock = asyncio.Lock()

    @property
    def metrics(self):
        return self.metrics_state.current

    def start_run(
        self,
        *,
        total: int,
        target_concurrency: int,
        launch_interval_sec: float,
        phase: str,
    ):
        """
        Initializes a new run of the scheduler, resetting metrics and pause state.

        Args:
            total (int): The total number of questions to be processed in this run.
            target_concurrency (int): The target concurrency level for this run.
            launch_interval_sec (float): The interval in seconds between question launches.
            phase (str): The current phase of the scheduler (e.g., "fixed", "dynamic").
        """
        self.pause_until = 0.0
        return self.metrics_state.start(
            total=total,
            target_concurrency=target_concurrency,
            launch_interval_sec=launch_interval_sec,
            phase=phase,
        )

    def progress_context(self):
        """
        Returns a context manager for the progress view, which can be used to display real-time
        metrics and progress during the execution of benchmark questions.
        If no progress view factory is provided, a null context is returned.

        Returns:
            AbstractContextManager[ProgressView | None]: A context manager for the progress view.
        """
        metrics = self.require_metrics()
        if self.progress_view_factory is None:
            return nullcontext(None)
        return self.progress_view_factory(metrics)

    def print_final_summary(self, progress_view: ProgressView | None) -> None:
        """
        Prints the final summary of the scheduler run, including metrics and any relevant
        information.
        """
        if progress_view is not None:
            self.console.print(progress_view.final_summary())

    async def execute_attempt(
        self,
        question: BenchmarkQuestion,
        attempt: int,
        **dispatch_fields: object,
    ) -> AttemptOutcome:
        """
        Executes a single attempt to answer a benchmark question, handling HTTP dispatch,
        grading, and metrics recording.
        """
        launch_rpm = await self.record_request_launch()
        in_flight = await self.record_inflight_start()

        self.emit(
            logging.DEBUG,
            "HTTP_DISPATCH",
            benchmark_id=question.benchmark_id,
            question_id=question.question_id,
            attempt=attempt,
            observed_in_flight=in_flight,
            observed_launch_rpm=launch_rpm,
            **dispatch_fields,
        )

        try:
            response = await self.inference_client.infer(question.question)

        except InferenceRateLimitedError as exc:
            # Returns an AttemptOutcome indicating that the request was rate-limited, including the
            # retry delay and reason for rate limiting.
            # Dealing with rate limiting or concurrency limits is handled by the scheduler, which
            # may adjust its behavior based on the
            # observed rate limit reason and retry delay.
            return AttemptOutcome(
                question=question,
                attempt=attempt,
                error=str(exc),
                error_type="rate_limited",
                retry_after_sec=exc.retry_after_sec,
                rate_limit_reason=getattr(exc, "reason", None),
                observed_launch_rpm=launch_rpm,
                observed_in_flight=in_flight,
            )

        except InferenceClientError as exc:
            return AttemptOutcome(
                question=question,
                attempt=attempt,
                error=str(exc),
                error_type="client_error",
                observed_launch_rpm=launch_rpm,
                observed_in_flight=in_flight,
            )

        finally:
            await self.record_inflight_end()

        await self.record_http_success(response.latency_ms)
        grade = self.grader.grade(
            answer=response.answer,
            expected_answer=question.expected_answer,
        )

        return AttemptOutcome(
            question=question,
            attempt=attempt,
            result=QuestionResult(
                benchmark_id=question.benchmark_id,
                question_id=question.question_id,
                question=question.question,
                expected_answer=question.expected_answer,
                answer=response.answer,
                correct=grade.correct,
                score=grade.score,
                latency_ms=response.latency_ms,
                attempts=attempt,
                status="success",
                error=None,
            ),
            observed_launch_rpm=launch_rpm,
            observed_in_flight=in_flight,
        )

    async def respect_global_pause(self) -> None:
        """
        This method checks if the scheduler is currently in a global pause state (e.g., due to rate
          limiting).
        If a global pause is in effect, it will wait until the pause duration has elapsed
        before allowing further question dispatches. This ensures that the scheduler respects
        any rate limiting or backpressure conditions imposed by the inference client or external
          systems.
        """
        while True:
            async with self.pause_lock:
                delay = self.pause_until - time.monotonic()
            if delay <= 0:
                return
            await asyncio.sleep(delay)

    async def set_global_pause(
        self,
        retry_after_sec: int,
        *,
        cause: str,
    ) -> None:
        """
        Sets a global pause for the scheduler, preventing further question dispatches until the
        specified retry_after_sec has elapsed. This is typically used in response to rate limiting
        events or other conditions that require throttling.
        """
        now = time.monotonic()
        candidate = now + retry_after_sec + random.uniform(0.0, 0.25)

        async with self.pause_lock:
            previous = self.pause_until
            self.pause_until = max(self.pause_until, candidate)
            pause_until = self.pause_until

        async with self.metrics_state.lock:
            self.require_metrics().add_wait_interval(now, pause_until)

        if previous <= now or candidate - previous >= 1.0:
            self.emit(
                logging.INFO,
                "BACKPRESSURE_PAUSE",
                cause=cause,
                duration_sec=f"{max(0.0, pause_until - now):.2f}",
            )

    def compute_retry_delay(
        self,
        outcome: AttemptOutcome,
        *,
        max_backoff_sec: int,
    ) -> float:
        """
        Computes the retry delay for a given attempt outcome, incorporating exponential backoff
        and jitter.

        Args:
            outcome (AttemptOutcome): The outcome of the attempt for which to compute the retry
            delay.
            max_backoff_sec (int): The maximum backoff time in seconds.

        Returns:
            float: The computed retry delay in seconds.
        """
        jitter = random.uniform(0.0, 0.25)
        if outcome.error_type == "rate_limited":
            return float(outcome.retry_after_sec or 1) + jitter
        return (
            min(
                2 ** (outcome.attempt - 1),
                max_backoff_sec,
            )
            + jitter
        )

    def build_failed_result(self, outcome: AttemptOutcome) -> QuestionResult:
        """
        Builds a QuestionResult object representing a failed attempt to answer a benchmark question.

        Args:
            outcome (AttemptOutcome): The outcome of the failed attempt.

        Returns:
            QuestionResult: A QuestionResult object representing the failed attempt, including
            relevant information such as the benchmark ID, question ID, error message, and status.
        """
        return QuestionResult(
            benchmark_id=outcome.question.benchmark_id,
            question_id=outcome.question.question_id,
            question=outcome.question.question,
            expected_answer=outcome.question.expected_answer,
            answer=None,
            correct=False,
            score=0.0,
            latency_ms=None,
            attempts=outcome.attempt,
            status="failed",
            error=outcome.error,
        )

    ## Metrics recording methods that delegate to SchedulerMetrics

    def record_request_launch(self):
        return self.metrics_state.record_launch()

    def record_inflight_start(self):
        return self.metrics_state.inflight_start()

    def record_inflight_end(self):
        return self.metrics_state.inflight_end()

    def record_http_success(self, latency_ms):
        return self.metrics_state.record_http_success(latency_ms)

    def record_retry(self):
        return self.metrics_state.record_retry()

    def record_rate_limit(self, kind):
        return self.metrics_state.record_rate_limit(kind)

    def record_completion(self, result):
        return self.metrics_state.record_completion(result)

    def refresh_metrics(self, **kwargs):
        return self.metrics_state.refresh(**kwargs)

    def require_metrics(self):
        return self.metrics_state.require()

    ## Event logging methods that delegate to the provided event_logger

    def emit(self, level: int, event: str, **fields: object) -> None:
        self.event_logger(self.logger, level, event, **fields)
