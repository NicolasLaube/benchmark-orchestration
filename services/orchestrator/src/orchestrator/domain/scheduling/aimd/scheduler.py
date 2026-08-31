"""
The orchestrator.
No logic.
"""

import asyncio
import logging
import time
from collections import deque
from uuid import UUID

from orchestrator.application.runtime import SchedulerRuntime
from orchestrator.domain.grading.substring import SubstringGrader
from orchestrator.domain.models.question_result import QuestionResult
from orchestrator.domain.scheduling.aimd.config import (
    AdaptiveAimdSchedulerConfig,
)
from orchestrator.domain.scheduling.aimd.controller import (
    AdaptiveAimdController,
)
from orchestrator.domain.scheduling.common.classify_rate_limit_reason import (
    RateLimitKind,
)
from orchestrator.domain.scheduling.common.delayed_retries import DelayedRetries
from orchestrator.domain.scheduling.common.models import AttemptOutcome, ControlUpdate
from orchestrator.domain.scheduling.common.observability import (
    log_final_summary,
    maybe_log_progress,
)
from orchestrator.infrastructure.inference_client.client import InferenceClient
from orchestrator.infrastructure.io.benchmark import BenchmarkQuestion
from orchestrator.infrastructure.messaging.redis.producer import RedisEventProducer


class AdaptiveAimdScheduler:
    def __init__(
        self,
        inference_client: InferenceClient,
        grader: SubstringGrader,
        event_producer: RedisEventProducer,
        config: AdaptiveAimdSchedulerConfig | None = None,
        **runtime_kwargs,
    ) -> None:
        self.config = config or AdaptiveAimdSchedulerConfig()
        self.controller = AdaptiveAimdController(self.config)
        self.runtime = SchedulerRuntime(
            inference_client,
            grader,
            event_producer=event_producer,
            **runtime_kwargs,
        )
        self.last_launch_at = 0.0
        self.launch_lock = asyncio.Lock()

    @property
    def metrics(self):
        return self.runtime.metrics

    async def run_questions(
        self,
        questions: list[BenchmarkQuestion],
        *,
        run_id: UUID,
    ) -> list[QuestionResult]:
        self._start_run(len(questions))
        pending = deque((question, 1) for question in questions)
        delayed = DelayedRetries()
        active: set[asyncio.Task[AttemptOutcome]] = set()
        results: list[QuestionResult] = []

        with self.runtime.progress_context() as progress_view:
            while pending or delayed or active:
                await self._refresh_metrics()

                if progress_view is not None:
                    progress_view.refresh()

                delayed.move_ready_to(pending)
                self._launch_available(pending, active)

                if not active:
                    delay = delayed.next_delay()
                    if delay is not None and delay > 0:
                        await asyncio.sleep(delay)
                    continue

                done, active = await asyncio.wait(
                    active,
                    timeout=delayed.next_delay(),
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in done:
                    result = await self._handle_outcome(
                        task.result(),
                        delayed=delayed,
                        results=results,
                    )

                    if result is not None:
                        await self.runtime.publish_result(
                            run_id=run_id,
                            result=result,
                        )

            await self._refresh_metrics()
            if progress_view is not None:
                progress_view.refresh()

        log_final_summary(
            self.runtime,
            scheduler="adaptive_aimd",
            extra_fields=self.controller.observability_fields(),
        )
        return results

    async def _handle_outcome(
        self,
        outcome: AttemptOutcome,
        *,
        delayed: DelayedRetries,
        results: list[QuestionResult],
    ) -> QuestionResult | None:
        if outcome.result is not None:
            result = outcome.result
            results.append(result)
            await self.runtime.record_completion(result)
            self._emit_control_update(self.controller.on_success())
            self._log_progress()
            return result

        if outcome.error_type == "rate_limited":
            await self._handle_rate_limit(outcome)

        if outcome.attempt <= self.config.max_retries:
            await self._schedule_retry(outcome, delayed)
            return None

        result = self.runtime.build_failed_result(outcome)
        results.append(result)
        await self.runtime.record_completion(result)
        self._log_progress()
        self.runtime.emit(
            logging.ERROR,
            "REQUEST_FAILED",
            benchmark_id=outcome.question.benchmark_id,
            question_id=outcome.question.question_id,
            attempts=outcome.attempt,
            error_type=outcome.error_type,
            error=outcome.error,
        )
        return result

    async def _schedule_retry(
        self,
        outcome: AttemptOutcome,
        delayed: DelayedRetries,
    ) -> None:
        delay = self.runtime.compute_retry_delay(
            outcome,
            max_backoff_sec=self.config.max_backoff_sec,
        )
        await self.runtime.record_retry()
        delayed.schedule(
            delay_sec=delay,
            question=outcome.question,
            attempt=outcome.attempt + 1,
        )
        self.runtime.emit(
            logging.DEBUG,
            "RETRY_SCHEDULED",
            benchmark_id=outcome.question.benchmark_id,
            question_id=outcome.question.question_id,
            current_attempt=outcome.attempt,
            next_attempt=outcome.attempt + 1,
            delay_sec=f"{delay:.2f}",
            cause=outcome.error_type,
        )

    async def _handle_rate_limit(self, outcome: AttemptOutcome) -> None:
        kind, discovered_reason = self.controller.classify_rate_limit(outcome)
        await self.runtime.record_rate_limit(kind)
        self.runtime.emit(
            logging.WARNING,
            "RATE_LIMIT",
            kind=str(kind),
            raw_reason=outcome.rate_limit_reason or "unknown",
            retry_after_sec=outcome.retry_after_sec,
            observed_in_flight=outcome.observed_in_flight,
            observed_launch_rpm=outcome.observed_launch_rpm,
        )

        if discovered_reason is not None:
            self.runtime.emit(
                logging.INFO,
                "RATE_LIMIT_SIGNAL_DISCOVERED",
                reason=discovered_reason,
                phase="→adaptive",
            )

        if kind == RateLimitKind.RPM:
            await self.runtime.set_global_pause(
                outcome.retry_after_sec or 1,
                cause="rpm_limit",
            )
            update = self.controller.on_rpm_limited(outcome)
        elif kind == RateLimitKind.CONCURRENCY:
            update = self.controller.on_concurrency_limited(outcome)
        else:
            await self.runtime.set_global_pause(
                outcome.retry_after_sec or 1,
                cause="generic_overload",
            )
            update = self.controller.on_generic_overload()

        self._emit_control_update(update)

    def _emit_control_update(self, update: ControlUpdate | None) -> None:
        if update is None:
            return

        fields: dict[str, object] = {
            "cause": update.cause,
            "target_concurrency": (
                f"{update.old_concurrency}→{self.controller.target_concurrency}"
            ),
            "launch_interval_sec": (
                f"{update.old_interval:.2f}→{self.controller.launch_interval_sec:.2f}"
            ),
            "phase": (
                f"{update.old_phase}→{self.controller.phase}"
                if update.old_phase != self.controller.phase
                else self.controller.phase
            ),
            "estimated_rpm_limit": self.controller.estimated_rpm_limit,
            "estimated_concurrency_limit": self.controller.estimated_concurrency_limit,
        }
        if update.event == "PROBE_COMPLETED":
            fields["successes"] = self.controller.probe_success_count

        self.runtime.emit(logging.INFO, update.event, **fields)

    def _start_run(self, total: int) -> None:
        self.controller.reset()
        self.last_launch_at = 0.0

        self.runtime.start_run(
            total=total,
            target_concurrency=self.controller.target_concurrency,
            launch_interval_sec=self.controller.launch_interval_sec,
            phase=self.controller.phase,
        )
        self.runtime.emit(
            logging.INFO,
            "RUN_STARTED",
            questions=total,
            scheduler="adaptive_aimd",
            phase=self.controller.phase,
            initial_concurrency=self.controller.target_concurrency,
            max_target_concurrency=self.config.max_target_concurrency,
            initial_launch_interval_sec=f"{self.controller.launch_interval_sec:.2f}",
            max_retries=self.config.max_retries,
        )

    def _launch_available(
        self,
        pending: deque[tuple[BenchmarkQuestion, int]],
        active: set[asyncio.Task[AttemptOutcome]],
    ) -> None:
        while pending and len(active) < self.controller.target_concurrency:
            question, attempt = pending.popleft()
            active.add(
                asyncio.create_task(
                    self._run_one_attempt(question, attempt),
                    name=(
                        f"benchmark={question.benchmark_id}:"
                        f"question={question.question_id}:"
                        f"attempt={attempt}"
                    ),
                )
            )

    async def _run_one_attempt(
        self,
        question: BenchmarkQuestion,
        attempt: int,
    ) -> AttemptOutcome:
        await self.runtime.respect_global_pause()
        await self._wait_launch_slot()

        return await self.runtime.execute_attempt(
            question,
            attempt,
            target_concurrency=self.controller.target_concurrency,
            launch_interval_sec=f"{self.controller.launch_interval_sec:.2f}",
        )

    async def _wait_launch_slot(self) -> None:
        async with self.launch_lock:
            wait = (
                self.last_launch_at
                + self.controller.launch_interval_sec
                - time.monotonic()
            )

            if wait > 0:
                await asyncio.sleep(wait)

            self.last_launch_at = time.monotonic()

    async def _refresh_metrics(self) -> None:
        await self.runtime.refresh_metrics(
            target_concurrency=self.controller.target_concurrency,
            launch_interval_sec=self.controller.launch_interval_sec,
            phase=self.controller.phase,
            estimated_rpm_limit=self.controller.estimated_rpm_limit,
            estimated_concurrency_limit=self.controller.estimated_concurrency_limit,
        )

    def _log_progress(self) -> None:
        maybe_log_progress(
            self.runtime,
            every=self.config.progress_log_every,
            extra_fields=self.controller.observability_fields(),
        )
