"""
This module defines the RunMetrics class, which serves as a single source of truth for tracking
metrics during an orchestrator run. It includes various attributes to monitor the progress,
performance, and state of the run, such as completion counts, HTTP attempts, rate limiting
information, latency measurements, and more. The class provides methods to calculate throughput,
accuracy, estimated time remaining (ETA), and other useful metrics.
The RunMetrics class is designed to be used in conjunction with the orchestrator's monitoring
and reporting systems, allowing for real-time tracking and analysis of benchmark runs.
It supports the collection of latency data
"""

import time
from dataclasses import dataclass, field

from orchestrator.utils import percentile


@dataclass(slots=True)
class RunMetrics:
    """Single source of truth for one orchestrator run."""

    total: int
    # Start time of the orchestrator run, used for calculating elapsed time and throughput.
    started_at: float = field(default_factory=time.monotonic)

    # Logical benchmark questions.
    # (Computes the number of completed questions, successes, failures, and correct answers.)
    completed: int = 0
    success: int = 0
    failure: int = 0
    correct: int = 0

    # HTTP attempts.
    http_attempts: int = 0
    http_successes: int = 0
    retries: int = 0

    # Rate limiting.
    rate_limited: int = 0
    rpm_limited: int = 0
    concurrency_limited: int = 0
    generic_overload: int = 0

    # Adaptive controller state.
    target_concurrency: int = 1
    http_in_flight: int = 0
    peak_http_in_flight: int = 0
    launch_rpm: int = 0
    launch_interval_sec: float = 0.0
    phase: str = "adaptive"
    estimated_rpm_limit: int | None = None
    estimated_concurrency_limit: int | None = None

    # Successful HTTP request latency.
    # Latencies are recorded in milliseconds and used to compute average latency, p50, and p95.
    latencies_ms: list[int] = field(default_factory=list)

    # Logical completion timestamps, used for a rolling throughput view.
    # Will be filled-in with the wall-clock time of each completed question, in seconds since the
    # epoch.
    completion_timestamps: list[float] = field(default_factory=list)

    # Wall-clock intervals caused by global Retry-After backpressure.
    wait_intervals: list[tuple[float, float]] = field(default_factory=list)

    def elapsed_sec(self) -> float:
        """Return the elapsed wall-clock time in seconds since the orchestrator run started."""
        return max(time.monotonic() - self.started_at, 0.0)

    def throughput(self) -> float:
        """Return the throughput (completed questions per second) since the orchestrator run
        started."""
        elapsed = self.elapsed_sec()
        if elapsed <= 0:
            return 0.0
        # just the number of completed questions divided by the elapsed time in seconds
        return self.completed / elapsed

    def throughput_rpm(self) -> float:
        """Return the throughput (completed questions per minute) since the orchestrator run
        started."""
        return self.throughput() * 60.0

    def recent_throughput(self, window_sec: float = 30.0) -> float:
        """Return the throughput (completed questions per second) over the last `window_sec`
        seconds. If there are no completions in the window, returns 0.0."""
        now = time.monotonic()
        window_start = max(self.started_at, now - window_sec)
        duration = max(now - window_start, 1e-9)

        # gets the number of completions that occurred within the specified time window
        completed_in_window = sum(
            timestamp >= window_start for timestamp in self.completion_timestamps
        )
        return completed_in_window / duration

    def recent_throughput_rpm(self, window_sec: float = 30.0) -> float:
        """Return the throughput (completed questions per minute) over the last `window_sec`
        seconds. If there are no completions in the window, returns 0.0."""
        return self.recent_throughput(window_sec) * 60.0

    def accuracy(self) -> float:
        """Return the percentage of correct answers among completed questions."""
        if self.completed <= 0:
            return 0.0
        return 100.0 * self.correct / self.completed

    def eta_sec(self) -> float | None:
        """Return the estimated time remaining in seconds, or None if it cannot be computed."""
        rate = self.recent_throughput()
        if rate <= 0:
            rate = self.throughput()
        if rate <= 0:
            return None

        # remaining time is computed from the number of remaining questions divided by the recent
        # throughput rate
        remaining = max(0, self.total - self.completed)
        return remaining / rate

    def average_latency_ms(self) -> float | None:
        """Return the average latency of successful HTTP requests in milliseconds, or None if no
        latencies are recorded."""
        if not self.latencies_ms:
            return None
        return sum(self.latencies_ms) / len(self.latencies_ms)

    def p50_latency_ms(self) -> int | None:
        """Return the 50th percentile (median) latency of successful HTTP requests in milliseconds,
        or None if no latencies are recorded."""
        return percentile(self.latencies_ms, 0.50)

    def p95_latency_ms(self) -> int | None:
        """Return the 95th percentile latency of successful HTTP requests in milliseconds,
        or None if no latencies are recorded."""
        return percentile(self.latencies_ms, 0.95)

    def wait_wall_sec(self) -> float:
        """Return the union of all global wait intervals."""
        if not self.wait_intervals:
            return 0.0

        intervals = sorted(self.wait_intervals)
        merged: list[tuple[float, float]] = []

        for start, end in intervals:
            if end <= start:
                continue

            if not merged or start > merged[-1][1]:
                merged.append((start, end))
                continue

            previous_start, previous_end = merged[-1]
            merged[-1] = (
                previous_start,
                max(previous_end, end),
            )

        return sum(end - start for start, end in merged)

    def useful_wall_sec(self) -> float:
        return max(
            0.0,
            self.elapsed_sec() - self.wait_wall_sec(),
        )

    def add_wait_interval(
        self,
        start: float,
        end: float,
    ) -> None:
        self.wait_intervals.append((start, end))
