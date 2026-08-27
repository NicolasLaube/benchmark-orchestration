import time
from datetime import UTC, datetime
from uuid import UUID

from orchestrator.application.config import (
    RunConfig,
    Settings,
)
from orchestrator.events.producer import RedisEventProducer
from orchestrator.events.redis import redis_client
from orchestrator.grader.substring import SubstringGrader
from orchestrator.inference_client.client import InferenceClient
from orchestrator.io.models import BenchmarkQuestion
from orchestrator.report.collector import MetricsCollector
from orchestrator.report.models import BenchmarkReport
from orchestrator.schedulers.aimd import AdaptiveAimdScheduler
from orchestrator.schedulers.aimd.config import AdaptiveAimdSchedulerConfig
from orchestrator.schedulers.fixed import FixedConcurrencyScheduler
from orchestrator.schedulers.fixed.config import FixedConcurrencySchedulerConfig


async def execute_benchmark(
    *,
    config: RunConfig,
    settings: Settings,
    questions: list[BenchmarkQuestion],
    run_id: UUID,
) -> BenchmarkReport:
    grader = SubstringGrader()

    async with InferenceClient(
        endpoint=settings.inference_endpoint,
        timeout_sec=settings.inference_timeout_seconds,
    ) as client:
        producer = RedisEventProducer(redis=redis_client)

        scheduler = _create_scheduler(
            config=config,
            client=client,
            grader=grader,
            event_producer=producer,
        )

        started_at = time.monotonic()

        results = await scheduler.run_questions(questions, run_id=run_id)

        total_wall_time_sec = time.monotonic() - started_at

    summary = MetricsCollector().summarize(
        results=results,
        total_wall_time_sec=total_wall_time_sec,
    )

    return BenchmarkReport(
        generated_at=datetime.now(UTC),
        summary=summary,
        results=results,
    )


def _create_scheduler(
    *,
    config: RunConfig,
    client: InferenceClient,
    grader: SubstringGrader,
    event_producer: RedisEventProducer,
) -> FixedConcurrencyScheduler | AdaptiveAimdScheduler:
    scheduler_config = config.scheduler

    if isinstance(
        scheduler_config,
        AdaptiveAimdSchedulerConfig,
    ):
        return AdaptiveAimdScheduler(
            inference_client=client,
            grader=grader,
            config=scheduler_config,
            event_producer=event_producer,
        )

    if isinstance(
        scheduler_config,
        FixedConcurrencySchedulerConfig,
    ):
        return FixedConcurrencyScheduler(
            inference_client=client,
            grader=grader,
            config=scheduler_config,
            event_producer=event_producer,
        )

    raise ValueError(f"Unsupported scheduler config: {type(scheduler_config).__name__}")
