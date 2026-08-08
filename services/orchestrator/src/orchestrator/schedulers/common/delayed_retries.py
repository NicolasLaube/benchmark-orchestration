"""
This module implements a delayed retries mechanism for benchmark questions. The `DelayedRetries`
class manages a queue of questions that need to be retried after a specified delay. It provides
methods to schedule retries, check for ready questions, and retrieve the next delay for pending
retries. This mechanism is useful for handling transient failures in benchmark tests, allowing
for controlled retries without overwhelming the system with immediate retry attempts.
"""

import time
from collections import deque

from orchestrator.loaders.models import BenchmarkQuestion


class DelayedRetries:
    def __init__(self) -> None:
        # A list of tuples containing the scheduled retry time, the question to be retried, and the
        # attempt number.
        # Important: The list is sorted by the scheduled retry time.
        self._items: list[tuple[float, BenchmarkQuestion, int]] = []

    def __bool__(self) -> bool:
        """Returns True if there are any pending retries, False otherwise.

        Returns:
            bool: True if there are pending retries, False otherwise.
        """
        return bool(self._items)

    def schedule(
        self,
        *,
        delay_sec: float,
        question: BenchmarkQuestion,
        attempt: int,
    ) -> None:
        """Schedules a retry for a question after a specified delay.

        Args:
            delay_sec (float): The delay in seconds before the retry should be attempted.
            question (BenchmarkQuestion): The benchmark question to be retried.
            attempt (int): The current attempt number for the question.
        """

        self._items.append(
            (
                time.monotonic() + delay_sec,
                question,
                attempt,
            )
        )

    def move_ready_to(
        self,
        pending: deque[tuple[BenchmarkQuestion, int]],
    ) -> None:
        """Moves ready questions from the delayed retries queue to the pending queue.

        Args:
            pending (deque[tuple[BenchmarkQuestion, int]]): The queue to which ready questions
            should be moved.
            Pending questions are represented as tuples of (BenchmarkQuestion, attempt number).

        """
        now = time.monotonic()
        # Move ready items to the pending queue and remove them from the delayed retries queue.
        ready = [item for item in self._items if item[0] <= now]
        # Remove ready items from the delayed retries queue.
        self._items[:] = [item for item in self._items if item[0] > now]
        # Add ready items to the pending queue.
        pending.extend((question, attempt) for _, question, attempt in ready)

    def next_delay(self) -> float | None:
        """
        Returns the delay in seconds until the next retry is ready, or None if there are no pending
        retries.

        Returns:
            float | None: The delay in seconds until the next retry is ready, or None if there are
            no pending retries.
        """
        if not self._items:
            return None

        # Since the list is sorted by scheduled retry time, the next ready item is the one with the
        # earliest scheduled retry time.
        next_ready_at = min(item[0] for item in self._items)
        return max(
            0.0,
            next_ready_at - time.monotonic(),
        )
