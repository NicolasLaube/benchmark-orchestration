"""
This module implements a fixed concurrency scheduler for orchestrating benchmark tests. The
`FixedConcurrencyScheduler` class manages the execution of benchmark questions with a specified
maximum concurrency level. It handles retries for failed requests, respects global pause signals,
and collects metrics for reporting. The scheduler uses an asynchronous approach to efficiently
manage concurrent requests while ensuring that the maximum concurrency limit is not exceeded.
"""

import asyncio
import logging
from uuid import UUID

from orchestrator.application.runtime import SchedulerRuntime
from orchestrator.domain.grading.substring import SubstringGrader
from orchestrator.domain.models.question_result import QuestionResult
from orchestrator.domain.scheduling.common.classify_rate_limit_reason import (
    classify_rate_limit_reason,
)
from orchestrator.domain.scheduling.common.observability import (
    log_final_summary,
    maybe_log_progress,
)
from orchestrator.domain.scheduling.fixed.config import (
    FixedConcurrencySchedulerConfig,
)
from orchestrator.infrastructure.inference_client.client import InferenceClient
from orchestrator.infrastructure.io.benchmark import BenchmarkQuestion
from orchestrator.infrastructure.messaging.redis.producer import RedisEventProducer


class FixedConcurrencyScheduler:
    def __init__(
        self,
        inference_client: InferenceClient,
        grader: SubstringGrader,
        event_producer: RedisEventProducer,
        config: FixedConcurrencySchedulerConfig | None = None,
        **runtime_kwargs,
    ) -> None:
        self.config = config or FixedConcurrencySchedulerConfig()

        self.runtime = SchedulerRuntime(
            inference_client,
            grader,
            event_producer=event_producer,
            **runtime_kwargs,
        )

        self.event_producer = event_producer

    @property
    def metrics(self):
        return self.runtime.metrics

    async def run_questions(
        self,
        questions: list[BenchmarkQuestion],
        run_id: UUID,
    ) -> list[QuestionResult]:

        # Start a new run in the runtime, initializing metrics and setting up the scheduler state.
        self.runtime.start_run(
            total=len(questions),
            target_concurrency=self.config.max_concurrency,
            launch_interval_sec=0.0,
            phase="fixed",
        )

        self.runtime.emit(
            logging.INFO,
            "RUN_STARTED",
            scheduler="fixed_concurrency",
            questions=len(questions),
            max_concurrency=self.config.max_concurrency,
            max_retries=self.config.max_retries,
        )

        # Semaphore is used to limit the number of concurrent tasks to the specified
        # max_concurrency.
        # Here, I chose not to use a thread pool executor because the asyncio.Semaphore is
        # sufficient for controlling concurrency
        # and the tasks are primarily I/O-bound (network requests), which is well-suited for asyncio
        semaphore = asyncio.Semaphore(self.config.max_concurrency)
        # max concurrency is fixed.
        tasks = [
            asyncio.create_task(self._run_one_question(question, semaphore))
            for question in questions
        ]
        results: list[QuestionResult] = []

        with self.runtime.progress_context() as progress_view:
            for task in asyncio.as_completed(tasks):
                result = await task
                results.append(result)
                await self.runtime.record_completion(result)

                if result is not None:
                    await self.runtime.publish_result(
                        run_id=run_id,
                        result=result,
                    )

                maybe_log_progress(
                    self.runtime,
                    every=self.config.progress_log_every,
                )

                if progress_view is not None:
                    progress_view.refresh()

        log_final_summary(
            self.runtime,
            scheduler="fixed_concurrency",
            extra_fields={"max_concurrency": self.config.max_concurrency},
        )
        return results

    async def _run_one_question(
        self,
        question: BenchmarkQuestion,
        semaphore: asyncio.Semaphore,
    ) -> QuestionResult:
        max_attempts = self.config.max_retries + 1
        last_outcome = None

        for attempt in range(1, max_attempts + 1):
            await self.runtime.respect_global_pause()

            async with semaphore:
                await self.runtime.respect_global_pause()
                outcome = await self.runtime.execute_attempt(
                    question,
                    attempt,
                    concurrency_limit=self.config.max_concurrency,
                )

            if outcome.result is not None:
                return outcome.result

            last_outcome = outcome

            if outcome.error_type == "rate_limited":
                kind = classify_rate_limit_reason(outcome.rate_limit_reason)
                await self.runtime.record_rate_limit(kind)
                self.runtime.emit(
                    logging.WARNING,
                    "RATE_LIMIT",
                    benchmark_id=question.benchmark_id,
                    question_id=question.question_id,
                    attempt=attempt,
                    kind=kind,
                    retry_after_sec=outcome.retry_after_sec,
                )

            if attempt >= max_attempts:
                break

            await self.runtime.record_retry()
            delay = self.runtime.compute_retry_delay(
                outcome,
                max_backoff_sec=self.config.max_backoff_sec,
            )

            if outcome.error_type == "rate_limited":
                await self.runtime.set_global_pause(
                    outcome.retry_after_sec or 1,
                    cause="rate_limit",
                )

            self.runtime.emit(
                logging.DEBUG,
                "RETRY_SCHEDULED",
                benchmark_id=question.benchmark_id,
                question_id=question.question_id,
                current_attempt=attempt,
                next_attempt=attempt + 1,
                delay_sec=f"{delay:.2f}",
                cause=outcome.error_type,
            )

            if outcome.error_type != "rate_limited":
                await asyncio.sleep(delay)

        assert last_outcome is not None

        self.runtime.emit(
            logging.ERROR,
            "REQUEST_FAILED",
            benchmark_id=question.benchmark_id,
            question_id=question.question_id,
            attempts=max_attempts,
            error=last_outcome.error,
        )
        return self.runtime.build_failed_result(last_outcome)
