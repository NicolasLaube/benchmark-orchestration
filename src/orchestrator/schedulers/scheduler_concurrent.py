import asyncio
import logging

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
        self._stats_lock = asyncio.Lock()

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

        semaphore = asyncio.Semaphore(self.max_concurrency)

        tasks = [
            self._run_one_with_semaphore(question, semaphore, total=len(questions))
            for question in questions
        ]

        logger.info(
            "Scheduler finished: completed=%d success=%d failures=%d retries=%d rate_limited=%d",
            self.completed_count,
            self.success_count,
            self.failure_count,
            self.retry_count,
            self.rate_limited_count,
        )

        return await asyncio.gather(*tasks)

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

        while attempts <= self.max_retries:
            attempts += 1

            try:
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

            except InferenceRateLimitedError as exc:
                last_error = str(exc)

                self.rate_limited_count += 1

                if attempts > self.max_retries:
                    break

                self.retry_count += 1

                logger.warning(
                    "Rate limited benchmark_id=%s question_id=%s attempt=%d retry_after=%ss",
                    question.benchmark_id,
                    question.question_id,
                    attempts,
                    exc.retry_after_sec,
                )

                await asyncio.sleep(exc.retry_after_sec)

            except InferenceClientError as exc:
                last_error = str(exc)

                if attempts > self.max_retries:
                    break

                self.retry_count += 1
                backoff_sec = min(2 ** (attempts - 1), self.max_backoff_sec)

                logger.warning(
                    "Inference error benchmark_id=%s question_id=%s attempt=%d backoff=%ss error=%s",
                    question.benchmark_id,
                    question.question_id,
                    attempts,
                    backoff_sec,
                    exc,
                )

                await asyncio.sleep(backoff_sec)

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
        async with self._stats_lock:
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
