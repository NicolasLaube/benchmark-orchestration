import logging

from orchestrator.schedulers.common.scheduler_runtime import SchedulerRuntime


def maybe_log_progress(
    runtime: SchedulerRuntime,
    *,
    every: int | None,
    extra_fields: dict[str, object] | None = None,
) -> None:
    if every is None:
        return

    metrics = runtime.require_metrics()
    if metrics.completed % every != 0 and metrics.completed != metrics.total:
        return

    fields: dict[str, object] = {
        "completed": f"{metrics.completed}/{metrics.total}",
        "success": metrics.success,
        "failure": metrics.failure,
        "throughput_req_sec": f"{metrics.throughput():.2f}",
        "http_in_flight": metrics.http_in_flight,
        "peak_http_in_flight": metrics.peak_http_in_flight,
        "launch_rpm": metrics.launch_rpm,
        "p50_ms": metrics.p50_latency_ms(),
        "p95_ms": metrics.p95_latency_ms(),
        "retries": metrics.retries,
        "rate_limits": metrics.rate_limited,
    }
    fields.update(extra_fields or {})
    runtime.emit(logging.INFO, "PROGRESS", **fields)


def log_final_summary(
    runtime: SchedulerRuntime,
    *,
    scheduler: str,
    extra_fields: dict[str, object] | None = None,
) -> None:
    metrics = runtime.require_metrics()

    fields: dict[str, object] = {
        "scheduler": scheduler,
        "completed": metrics.completed,
        "successful": metrics.success,
        "failed": metrics.failure,
        "http_attempts": metrics.http_attempts,
        "retries": metrics.retries,
        "elapsed_sec": f"{metrics.elapsed_sec():.2f}",
        "throughput_req_sec": f"{metrics.throughput():.2f}",
        "accuracy": f"{metrics.accuracy():.2f}%",
        "peak_http_in_flight": metrics.peak_http_in_flight,
        "p50_ms": metrics.p50_latency_ms(),
        "p95_ms": metrics.p95_latency_ms(),
        "rate_limits": metrics.rate_limited,
        "rpm_429": metrics.rpm_limited,
        "concurrency_429": metrics.concurrency_limited,
        "generic_429": metrics.generic_overload,
    }
    fields.update(extra_fields or {})
    runtime.emit(logging.INFO, "RUN_FINISHED", **fields)
