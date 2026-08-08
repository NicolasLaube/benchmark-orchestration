"""
The orchestrator.
No logic.
"""

import asyncio
import logging
import time
from collections import deque

from orchestrator.grader.substring import SubstringGrader
from orchestrator.inference_client.client import InferenceClient
from orchestrator.loaders.benchmark import BenchmarkQuestion
from orchestrator.report.models import QuestionResult
from orchestrator.schedulers.aimd.config import (
    AdaptiveAimdSchedulerConfig,
)
from orchestrator.schedulers.aimd.controller import (
    AdaptiveAimdController,
)
from orchestrator.schedulers.aimd.outcome_handler import (
    controller_fields,
)
from orchestrator.schedulers.aimd.outcomes import (
    handle_outcome,
)
from orchestrator.schedulers.common.delayed_retries import DelayedRetries
from orchestrator.schedulers.common.models import AttemptOutcome
from orchestrator.schedulers.common.observability import (
    log_final_summary,
    maybe_log_progress,
)
from orchestrator.schedulers.common.runtime import SchedulerRuntime


class AdaptiveAimdScheduler:
    def __init__(
        self,
        inference_client: InferenceClient,
        grader: SubstringGrader,
        config: AdaptiveAimdSchedulerConfig | None = None,
        **runtime_kwargs,
    ) -> None:
        self.config = config or AdaptiveAimdSchedulerConfig()
        self.controller = AdaptiveAimdController(self.config)
        self.runtime = SchedulerRuntime(
            inference_client,
            grader,
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
                    await handle_outcome(
                        outcome=task.result(),
                        runtime=self.runtime,
                        controller=self.controller,
                        config=self.config,
                        delayed=delayed,
                        results=results,
                        log_progress=self._log_progress,
                    )

            await self._refresh_metrics()
            if progress_view is not None:
                progress_view.refresh()

        self.runtime.print_final_summary(progress_view)
        log_final_summary(
            self.runtime,
            scheduler="adaptive_aimd",
            extra_fields=controller_fields(self.controller),
        )
        return results

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
            wait = self.last_launch_at + self.controller.launch_interval_sec - time.monotonic()

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
            extra_fields=controller_fields(self.controller),
        )
