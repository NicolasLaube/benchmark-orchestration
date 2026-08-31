from datetime import datetime
from uuid import UUID

from orchestrator.infrastructure.persistence.models.runs import RunModel
from sqlalchemy import select, update
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

    async def increment_completed(
        self,
        run_id: UUID,
    ) -> None:
        await self.session.execute(
            update(RunModel)
            .where(RunModel.id == run_id)
            .values(completed=RunModel.completed + 1)
        )

    async def mark_started(
        self,
        run_id: UUID,
        started_at: datetime,
    ) -> None:
        await self.session.execute(
            update(RunModel)
            .where(RunModel.id == run_id)
            .values(
                status="running",
                started_at=started_at,
            )
        )

    async def mark_finished(
        self,
        run_id: UUID,
        finished_at: datetime,
    ) -> None:
        await self.session.execute(
            update(RunModel)
            .where(RunModel.id == run_id)
            .values(
                status="finished",
                finished_at=finished_at,
            )
        )
