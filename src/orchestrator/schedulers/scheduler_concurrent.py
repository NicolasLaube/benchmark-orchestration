import asyncio
import logging
import random
import time

from orchestrator.graders.grader import SubstringGrader
from orchestrator.inference_client import (
    InferenceClient,
    InferenceClientError,
    InferenceRateLimitedError,
)
from orchestrator.models import BenchmarkQuestion, QuestionResult

logger = logging.getLogger(__name__)


class FixedConcurrencyScheduler:
    def __init__(
        self,
        inference_client: InferenceClient,
        grader: SubstringGrader,
        max_concurrency: int = 4,
        max_retries: int = 3,
        max_backoff_sec: float = 8.0,
        progress_every: int = 10,
    ) -> None:
        """Scheduler that runs questions with a fixed concurrency limit and retry logic."""

        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than 0")

        if max_retries < 0:
            raise ValueError("max_retries must be greater than or equal to 0")

        self.inference_client = inference_client
        self.grader = grader
        self.max_concurrency = max_concurrency
        self.max_retries = max_retries
        self.max_backoff_sec = max_backoff_sec

        self.progress_every = progress_every
        self.completed_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.retry_count = 0
        self.rate_limited_count = 0

        self.pause_until = 0.0
        self.pause_lock = asyncio.Lock()
        self.stats_lock = asyncio.Lock()

    async def run_questions(
        self,
        questions: list[BenchmarkQuestion],
    ) -> list[QuestionResult]:
        logger.info(
            "Starting fixed-concurrency scheduler: total=%d max_concurrency=%d max_retries=%d",
            len(questions),
            self.max_concurrency,
            self.max_retries,
        )

        # The semaphore limits the number of concurrent tasks to max_concurrency.
        # Interesting thing to note: it is better than batching because it allows for more efficient
        # use of resources. If one task is slow, it doesn't block the others from starting.
        semaphore = asyncio.Semaphore(self.max_concurrency)

        # Create a list of tasks, each of which will run a question with the semaphore.
        tasks = [
            self._run_one_with_semaphore(question, semaphore, total=len(questions))
            for question in questions
        ]

        # Run all tasks concurrently, respecting the semaphore limit.
        results = await asyncio.gather(*tasks)

        logger.info(
            "Scheduler finished: completed=%d success=%d failures=%d retries=%d rate_limited=%d",
            self.completed_count,
            self.success_count,
            self.failure_count,
            self.retry_count,
            self.rate_limited_count,
        )

        return results

    async def _run_one_with_semaphore(
        self,
        question: BenchmarkQuestion,
        semaphore: asyncio.Semaphore,
        total: int,
    ) -> QuestionResult:
        async with semaphore:
            result = await self._run_one_with_retries(question)

        await self._record_completion(result, total)

        return result

    async def _run_one_with_retries(
        self,
        question: BenchmarkQuestion,
    ) -> QuestionResult:
        attempts = 0
        last_error: str | None = None

        max_attempts = self.max_retries + 1

        while attempts < max_attempts:
            attempts += 1

            try:
                await self._respect_global_pause()

                inference_result = await self.inference_client.infer(question.question)

                grade_result = self.grader.grade(
                    answer=inference_result.answer,
                    expected_answer=question.expected_answer,
                )

                logger.debug(
                    "Success benchmark_id=%s question_id=%s attempt=%d latency_ms=%d correct=%s",
                    question.benchmark_id,
                    question.question_id,
                    attempts,
                    inference_result.latency_ms,
                    grade_result.correct,
                )

                return QuestionResult(
                    benchmark_id=question.benchmark_id,
                    question_id=question.question_id,
                    question=question.question,
                    expected_answer=question.expected_answer,
                    answer=inference_result.answer,
                    correct=grade_result.correct,
                    score=grade_result.score,
                    latency_ms=inference_result.latency_ms,
                    attempts=attempts,
                    status="success",
                    error=None,
                )

            # Logic when the inference client returns a rate limit error (HTTP 429).
            except InferenceRateLimitedError as exc:
                last_error = str(exc)

                async with self.stats_lock:
                    self.rate_limited_count += 1

                if attempts >= max_attempts:
                    logger.error(
                        "Rate limit final failure benchmark_id=%s question_id=%s attempts=%d retry_after=%ss",
                        question.benchmark_id,
                        question.question_id,
                        attempts,
                        exc.retry_after_sec,
                    )
                    break

                await self._handle_rate_limit_retry(exc, question, attempts)

            # Logic when the inference client returns a non-rate limit error (e.g., HTTP 500).
            except InferenceClientError as exc:
                last_error = str(exc)

                if attempts >= max_attempts:
                    logger.error(
                        "Inference final failure benchmark_id=%s question_id=%s attempts=%d error=%s",
                        question.benchmark_id,
                        question.question_id,
                        attempts,
                        exc,
                    )
                    break

                async with self.stats_lock:
                    self.retry_count += 1

                backoff_sec = min(2 ** (attempts - 1), self.max_backoff_sec)
                jitter = random.uniform(0.0, 0.25)
                sleep_sec = backoff_sec + jitter

                logger.error(
                    "Inference error benchmark_id=%s question_id=%s attempt=%d backoff=%.2fs error=%s",
                    question.benchmark_id,
                    question.question_id,
                    attempts,
                    sleep_sec,
                    exc,
                )

                await asyncio.sleep(sleep_sec)

        return QuestionResult(
            benchmark_id=question.benchmark_id,
            question_id=question.question_id,
            question=question.question,
            expected_answer=question.expected_answer,
            answer=None,
            correct=False,
            score=0.0,
            latency_ms=None,
            attempts=attempts,
            status="failed",
            error=last_error,
        )

    async def _record_completion(
        self,
        result: QuestionResult,
        total: int,
    ) -> None:
        """Records the completion of a question, updating the counts and
        logging progress if needed."""
        async with self.stats_lock:
            self.completed_count += 1

            if result.status == "success":
                self.success_count += 1
            else:
                self.failure_count += 1

            if self.completed_count % self.progress_every == 0 or self.completed_count == total:
                logger.info(
                    "Progress: %d/%d completed | success=%d failures=%d retries=%d 429s=%d",
                    self.completed_count,
                    total,
                    self.success_count,
                    self.failure_count,
                    self.retry_count,
                    self.rate_limited_count,
                )

    async def _respect_global_pause(self) -> None:
        async with self.pause_lock:
            delay = self.pause_until - time.monotonic()

        if delay > 0:
            logger.info("Global backpressure pause: sleeping %.2fs", delay)
            await asyncio.sleep(delay)

    async def _set_global_pause(self, retry_after_sec: int) -> None:
        """Sets a global pause for all tasks to respect, based on the retry_after_sec from a
        rate limit error. Adds a small random jitter to avoid thundering herd problems."""

        jitter = random.uniform(0.0, 0.25)
        pause_until = time.monotonic() + retry_after_sec + jitter

        async with self.pause_lock:
            self.pause_until = max(self.pause_until, pause_until)

    async def _handle_rate_limit_retry(
        self,
        exc: InferenceRateLimitedError,
        question: BenchmarkQuestion,
        attempts: int,
    ) -> None:
        """Handles the logic for retrying after a rate limit error, including setting
        a global pause and logging."""
        await self._set_global_pause(exc.retry_after_sec)

        async with self.stats_lock:
            self.retry_count += 1

        logger.warning(
            "Rate limited benchmark_id=%s question_id=%s attempt=%d retry_after=%ss",
            question.benchmark_id,
            question.question_id,
            attempts,
            exc.retry_after_sec,
        )

        await self._respect_global_pause()
