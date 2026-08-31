from datetime import datetime
from uuid import UUID

from orchestrator.infrastructure.persistence.models.report import RunReportModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class RunReportRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(
        self,
        run_id: UUID,
        report: dict,
        generated_at: datetime,
    ) -> None:
        self.session.add(
            RunReportModel(
                run_id=run_id,
                report=report,
                generated_at=generated_at,
            )
        )

    async def get(self, run_id: UUID) -> RunReportModel | None:
        stmt = select(RunReportModel).where(RunReportModel.run_id == run_id)

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()
