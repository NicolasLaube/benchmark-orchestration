import logging

from orchestrator.schedulers.common.classify_rate_limit_reason import RateLimitKind
from orchestrator.schedulers.common.scheduler_models import AttemptOutcome, ControlUpdate
from orchestrator.schedulers.common.scheduler_runtime import SchedulerRuntime
from orchestrator.schedulers.scheduler_aimd_v3.scheduler_aimd_controller import (
    AdaptiveAimdController,
)


async def handle_rate_limit(
    runtime: SchedulerRuntime,
    controller: AdaptiveAimdController,
    outcome: AttemptOutcome,
) -> None:
    kind, discovered_reason = controller.classify_rate_limit(outcome)
    await runtime.record_rate_limit(kind)

    runtime.emit(
        logging.WARNING,
        "RATE_LIMIT",
        kind=str(kind),
        raw_reason=outcome.rate_limit_reason or "unknown",
        retry_after_sec=outcome.retry_after_sec,
        observed_in_flight=outcome.observed_in_flight,
        observed_launch_rpm=outcome.observed_launch_rpm,
    )

    if discovered_reason is not None:
        runtime.emit(
            logging.INFO,
            "RATE_LIMIT_SIGNAL_DISCOVERED",
            reason=discovered_reason,
            phase="→adaptive",
        )

    if kind == RateLimitKind.RPM:
        await runtime.set_global_pause(
            outcome.retry_after_sec or 1,
            cause="rpm_limit",
        )
        update = controller.on_rpm_limited(outcome)

    elif kind == RateLimitKind.CONCURRENCY:
        update = controller.on_concurrency_limited(outcome)

    else:
        await runtime.set_global_pause(
            outcome.retry_after_sec or 1,
            cause="generic_overload",
        )
        update = controller.on_generic_overload()

    emit_control_update(runtime, controller, update)


def emit_control_update(
    runtime: SchedulerRuntime,
    controller: AdaptiveAimdController,
    update: ControlUpdate | None,
) -> None:
    """Emits a control update event to the runtime, capturing the state of the scheduler before and
    after the update. If no update is provided, no event is emitted."""
    if update is None:
        return

    fields: dict[str, object] = {
        "cause": update.cause,
        "target_concurrency": (f"{update.old_concurrency}→{controller.target_concurrency}"),
        "launch_interval_sec": (f"{update.old_interval:.2f}→{controller.launch_interval_sec:.2f}"),
        "phase": (
            f"{update.old_phase}→{controller.phase}"
            if update.old_phase != controller.phase
            else controller.phase
        ),
        "estimated_rpm_limit": controller.estimated_rpm_limit,
        "estimated_concurrency_limit": controller.estimated_concurrency_limit,
    }

    if update.event == "PROBE_COMPLETED":
        fields["successes"] = controller.probe_success_count

    runtime.emit(
        logging.INFO,
        update.event,
        **fields,
    )


def controller_fields(
    controller: AdaptiveAimdController,
) -> dict[str, object]:
    return {
        "target_concurrency": controller.target_concurrency,
        "launch_interval_sec": f"{controller.launch_interval_sec:.2f}",
        "phase": controller.phase,
        "estimated_rpm_limit": controller.estimated_rpm_limit,
        "estimated_concurrency_limit": controller.estimated_concurrency_limit,
        "structured_429_seen": controller.structured_429_seen,
    }
