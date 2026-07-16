import logging
from collections.abc import Callable

from orchestrator.report.report_models import QuestionResult
from orchestrator.schedulers.common.delayed_retries import DelayedRetries
from orchestrator.schedulers.common.scheduler_models import AttemptOutcome
from orchestrator.schedulers.common.scheduler_runtime import SchedulerRuntime
from orchestrator.schedulers.scheduler_aimd_v3.scheduler_aimd_config import (
    AdaptiveAimdConfig,
)
from orchestrator.schedulers.scheduler_aimd_v3.scheduler_aimd_controller import (
    AdaptiveAimdController,
)
from orchestrator.schedulers.scheduler_aimd_v3.scheduler_aimd_events import (
    emit_control_update,
    handle_rate_limit,
)


async def handle_outcome(
    *,
    outcome: AttemptOutcome,
    runtime: SchedulerRuntime,
    controller: AdaptiveAimdController,
    config: AdaptiveAimdConfig,
    delayed: DelayedRetries,
    results: list[QuestionResult],
    log_progress: Callable[[], None],
) -> None:
    """Handles the outcome of a benchmark question attempt, updating metrics, scheduling retries,
    and emitting control updates as necessary."""
    if outcome.result is not None:
        # Record the successful completion of the question attempt, update metrics,
        # and emit a control update.
        results.append(outcome.result)
        await runtime.record_completion(outcome.result)
        emit_control_update(
            runtime,
            controller,
            controller.on_success(),
        )
        log_progress()
        return

    if outcome.error_type == "rate_limited":
        # Handle rate limiting by classifying the type of rate limit, updating metrics, and emitting
        # control updates. If the maximum number of retries has not been reached, schedule a retry
        # for the question attempt.
        await handle_rate_limit(
            runtime,
            controller,
            outcome,
        )

    if outcome.attempt <= config.max_retries:
        # Schedule a retry for the question attempt, respecting the maximum backoff time.
        delay = runtime.compute_retry_delay(
            outcome,
            max_backoff_sec=config.max_backoff_sec,
        )
        await runtime.record_retry()
        delayed.schedule(
            delay_sec=delay,
            question=outcome.question,
            attempt=outcome.attempt + 1,
        )
        runtime.emit(
            logging.DEBUG,
            "RETRY_SCHEDULED",
            benchmark_id=outcome.question.benchmark_id,
            question_id=outcome.question.question_id,
            current_attempt=outcome.attempt,
            next_attempt=outcome.attempt + 1,
            delay_sec=f"{delay:.2f}",
            cause=outcome.error_type,
        )
        return

    failed = runtime.build_failed_result(outcome)
    results.append(failed)
    await runtime.record_completion(failed)
    log_progress()

    runtime.emit(
        logging.ERROR,
        "REQUEST_FAILED",
        benchmark_id=outcome.question.benchmark_id,
        question_id=outcome.question.question_id,
        attempts=outcome.attempt,
        error_type=outcome.error_type,
        error=outcome.error,
    )
