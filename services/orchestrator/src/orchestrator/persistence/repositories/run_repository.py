from uuid import UUID

from orchestrator.persistence.models import RunModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class RunRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, run: RunModel) -> None:

        self.session.add(run)

        await self.session.commit()

    async def get(self, run_id: UUID) -> RunModel | None:
        result = await self.session.execute(
            select(RunModel).where(RunModel.id == run_id)
        )

        return result.scalar_one_or_none()
