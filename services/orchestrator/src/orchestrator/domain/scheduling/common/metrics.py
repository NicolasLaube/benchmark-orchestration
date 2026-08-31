"""
This module defines the `SchedulerMetrics` class, which is responsible for tracking and managing
metrics related to the scheduling of benchmark questions. It provides methods to record various
events such as question launches, completions, successes, retries, and rate limiting. The class
maintains a current `RunMetrics` instance that aggregates these metrics, allowing for real-time
monitoring and reporting of the scheduler's performance. It also includes functionality to
prune old launch timestamps to maintain an accurate launch rate per minute (RPM) metric.
"""

import asyncio
import time
from collections import deque

from orchestrator.domain.models.question_result import QuestionResult
from orchestrator.domain.run_metrics import RunMetrics


class SchedulerMetrics:
    def __init__(self) -> None:
        self.current: RunMetrics | None = None
        self.launch_timestamps: deque[float] = deque()
        # A lock to ensure thread-safe access to the metrics state and launch timestamps. This is
        # important because the scheduler may be running in an asynchronous context where multiple
        # coroutines could be updating the metrics concurrently.
        self.lock = asyncio.Lock()

    def start(
        self,
        *,
        total: int,
        target_concurrency: int,
        launch_interval_sec: float,
        phase: str,
    ) -> RunMetrics:
        """Starts a new run of the scheduler metrics tracking.

        Args:
            total (int): The total number of questions to be processed in this run.
            target_concurrency (int): The target concurrency level for this run.
            launch_interval_sec (float): The interval in seconds between question launches.
            phase (str): The current phase of the scheduler (e.g., "fixed", "dynamic").
            Phase can be used to differentiate between different stages of the scheduling process,
            such as
            initial launch, retry handling, or any other custom phases defined by the scheduler.

        Returns:
            RunMetrics: The newly created RunMetrics instance for this run.
        """

        self.launch_timestamps.clear()
        self.current = RunMetrics(
            total=total,
            target_concurrency=target_concurrency,
            launch_interval_sec=launch_interval_sec,
            phase=phase,
        )
        return self.current

    async def record_launch(self) -> int:
        """Records a question launch event and updates the launch rate per minute (RPM)."""
        now = time.monotonic()
        async with self.lock:
            metrics = self.require()
            metrics.http_attempts += 1
            self.launch_timestamps.append(now)
            self._prune(now)
            metrics.launch_rpm = len(self.launch_timestamps)
            return metrics.launch_rpm

    async def inflight_start(self) -> int:
        """Records the start of an in-flight HTTP request."""
        async with self.lock:
            metrics = self.require()
            metrics.http_in_flight += 1
            metrics.peak_http_in_flight = max(
                metrics.peak_http_in_flight,
                metrics.http_in_flight,
            )
            return metrics.http_in_flight

    async def inflight_end(self) -> None:
        """Records the end of an in-flight HTTP request."""
        async with self.lock:
            metrics = self.require()
            metrics.http_in_flight = max(0, metrics.http_in_flight - 1)

    async def record_http_success(self, latency_ms: int) -> None:
        """Records a successful HTTP request and its latency in milliseconds."""
        async with self.lock:
            metrics = self.require()
            metrics.http_successes += 1
            metrics.latencies_ms.append(latency_ms)

    async def record_retry(self) -> None:
        """Records a retry attempt."""
        async with self.lock:
            self.require().retries += 1

    async def record_rate_limit(self, kind: str) -> None:
        """Records a rate limit event of the specified kind."""
        async with self.lock:
            metrics = self.require()
            metrics.rate_limited += 1
            if kind == "rpm":
                metrics.rpm_limited += 1
            elif kind == "concurrency":
                metrics.concurrency_limited += 1
            else:
                metrics.generic_overload += 1

    async def record_completion(self, result: QuestionResult) -> None:
        """Records the completion of a question attempt."""
        async with self.lock:
            metrics = self.require()
            metrics.completed += 1
            if hasattr(metrics, "completion_timestamps"):
                metrics.completion_timestamps.append(time.monotonic())

            if result.status == "success":
                metrics.success += 1
                if result.correct:
                    metrics.correct += 1
            else:
                metrics.failure += 1

    async def refresh(
        self,
        *,
        target_concurrency: int,
        launch_interval_sec: float,
        phase: str,
        estimated_rpm_limit: int | None = None,
        estimated_concurrency_limit: int | None = None,
    ) -> None:
        """Refreshes the current metrics with updated values."""
        now = time.monotonic()
        async with self.lock:
            metrics = self.require()
            self._prune(now)
            metrics.target_concurrency = target_concurrency
            metrics.launch_rpm = len(self.launch_timestamps)
            metrics.launch_interval_sec = launch_interval_sec
            metrics.phase = phase
            metrics.estimated_rpm_limit = estimated_rpm_limit
            metrics.estimated_concurrency_limit = estimated_concurrency_limit

    def require(self) -> RunMetrics:
        """Returns the current RunMetrics instance, raising an error if it is not initialized."""
        if self.current is None:
            raise RuntimeError("scheduler metrics are not initialized")
        return self.current

    def _prune(self, now: float) -> None:
        """Prunes old launch timestamps that are older than 60 seconds to maintain an accurate
        launch rate per minute (RPM) metric.
        """
        while self.launch_timestamps and now - self.launch_timestamps[0] > 60.0:
            self.launch_timestamps.popleft()
