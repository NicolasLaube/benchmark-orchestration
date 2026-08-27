import asyncio
from uuid import UUID

from redis.exceptions import ResponseError

from orchestrator.events.constants import (
    BENCHMARK_EVENTS_STREAM,
    PERSISTENCE_GROUP,
)
from orchestrator.events.redis import redis_client
from orchestrator.persistence.db import SessionLocal
from orchestrator.persistence.models.question_result import QuestionResultModel
from orchestrator.persistence.repositories.processed_event import (
    ProcessedEventRepository,
)
from orchestrator.persistence.repositories.question_result import (
    QuestionResultRepository,
)
from orchestrator.persistence.repositories.run import RunRepository

CONSUMER_NAME = "persistence-worker-1"


class PersistenceConsumer:
    async def ensure_group(self) -> None:
        try:
            await redis_client.xgroup_create(
                name=BENCHMARK_EVENTS_STREAM,
                groupname=PERSISTENCE_GROUP,
                id="0",
                mkstream=True,
            )
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def run(self) -> None:
        await self.ensure_group()

        while True:
            streams = await redis_client.xreadgroup(
                groupname=PERSISTENCE_GROUP,
                consumername=CONSUMER_NAME,
                streams={BENCHMARK_EVENTS_STREAM: ">"},
                count=10,
                block=5000,
            )

            for _, messages in streams:
                for event_id, fields in messages:
                    await self._handle_event(
                        event_id=event_id,
                        fields=fields,
                    )

    async def _handle_event(
        self,
        event_id: str,
        fields: dict[str, str],
    ) -> None:
        event_type = fields.get("type")

        if event_type != "question_completed":
            await redis_client.xack(
                BENCHMARK_EVENTS_STREAM,
                PERSISTENCE_GROUP,
                event_id,
            )
            return

        try:
            async with SessionLocal() as session:
                processed_repo = ProcessedEventRepository(session)
                result_repo = QuestionResultRepository(session)
                run_repo = RunRepository(session)

                # Idempotence condition
                if await processed_repo.exists(event_id):
                    print("Event already exists")
                    await redis_client.xack(
                        BENCHMARK_EVENTS_STREAM,
                        PERSISTENCE_GROUP,
                        event_id,
                    )
                    return

                if fields.get("type") == "question_completed":
                    result = QuestionResultModel(
                        run_id=UUID(fields["run_id"]),
                        question_id=fields["question_id"],
                        success=fields["success"] == "True",
                        latency_ms=(
                            float(fields["latency_ms"])
                            if fields.get("latency_ms")
                            else None
                        ),
                        attempts=int(fields["attempts"]),
                        answer=fields.get("answer") or None,
                        error=fields.get("error") or None,
                    )

                    await result_repo.create(result)

                    await run_repo.increment_completed(UUID(fields["run_id"]))

                await processed_repo.create(event_id)

                await session.commit()

        except Exception as exc:
            raise RuntimeError("Failed to persist question result") from exc

        await redis_client.xack(
            BENCHMARK_EVENTS_STREAM,
            PERSISTENCE_GROUP,
            event_id,
        )


async def main() -> None:
    consumer = PersistenceConsumer()
    await consumer.run()


if __name__ == "__main__":
    # creates a separate thread for consumer
    asyncio.run(main())
