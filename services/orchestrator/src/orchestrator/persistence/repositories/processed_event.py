from orchestrator.persistence.models.processed_events import ProcessedEventModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ProcessedEventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def exists(self, event_id: str) -> bool:
        result = await self.session.execute(
            select(ProcessedEventModel.event_id).where(
                ProcessedEventModel.event_id == event_id
            )
        )

        return result.scalar_one_or_none() is not None

    async def create(self, event_id: str) -> None:
        self.session.add(
            ProcessedEventModel(
                event_id=event_id,
            )
        )
