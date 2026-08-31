
from orchestrator.domain.events import QuestionCompleted, RunCompleted
from orchestrator.infrastructure.messaging.redis.constants import (
    BENCHMARK_EVENTS_STREAM,
)
from redis.asyncio import Redis


class RedisEventProducer:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def publish_question_completed(
        self,
        event: QuestionCompleted,
    ) -> None:
        await self.redis.xadd(
            BENCHMARK_EVENTS_STREAM,
            {
                "type": "question_completed",
                "run_id": str(event.run_id),
                "question_id": event.question_id,
                "success": str(event.success),
                "latency_ms": (
                    "" if event.latency_ms is None else str(event.latency_ms)
                ),
                "attempts": str(event.attempts),
                "answer": event.answer or "",
                "error": event.error or "",
            },
        )

    async def publish_run_completed(self, event: RunCompleted) -> None:

        await self.redis.xadd(
            BENCHMARK_EVENTS_STREAM,
            {
                "type": "run_completed",
                "run_id": str(event.run_id),
                "finished_at": str(event.finished_at),
            },
        )
