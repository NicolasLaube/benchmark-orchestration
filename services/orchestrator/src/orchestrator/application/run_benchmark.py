from datetime import UTC, datetime
from uuid import UUID

from orchestrator.application.config import (
    RunConfig,
    Settings,
)
from orchestrator.domain.events import RunCompleted
from orchestrator.domain.grading.substring import SubstringGrader
from orchestrator.domain.models.question import BenchmarkQuestion
from orchestrator.domain.scheduling.aimd import AdaptiveAimdScheduler
from orchestrator.domain.scheduling.aimd.config import AdaptiveAimdSchedulerConfig
from orchestrator.domain.scheduling.fixed import FixedConcurrencyScheduler
from orchestrator.domain.scheduling.fixed.config import FixedConcurrencySchedulerConfig
from orchestrator.infrastructure.inference_client.client import InferenceClient
from orchestrator.infrastructure.messaging.redis.client import redis_client
from orchestrator.infrastructure.messaging.redis.producer import RedisEventProducer
from orchestrator.infrastructure.persistence.db import SessionLocal
from orchestrator.infrastructure.persistence.repositories.run import RunRepository
from orchestrator.interfaces.api.schemas.report import BenchmarkReport


async def execute_benchmark(
    *,
    config: RunConfig,
    settings: Settings,
    questions: list[BenchmarkQuestion],
    run_id: UUID,
) -> BenchmarkReport:
    started_at = datetime.now(UTC)

    async with SessionLocal() as session:
        run_repository = RunRepository(session)

        await run_repository.mark_started(
            run_id=run_id,
            started_at=started_at,
        )

        await session.commit()

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

        await scheduler.run_questions(questions, run_id=run_id)

    finished_at = datetime.now(UTC)

    async with SessionLocal() as session:
        run_repository = RunRepository(session)

        await run_repository.mark_finished(
            run_id=run_id,
            finished_at=finished_at,
        )

        await session.commit()

    await producer.publish_run_completed(
        RunCompleted(
            run_id=run_id,
            finished_at=finished_at,
        )
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
