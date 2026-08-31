from collections.abc import Sequence
from uuid import UUID

from orchestrator.infrastructure.persistence.models.question_result import (
    QuestionResultModel,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class QuestionResultRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, question_result: QuestionResultModel) -> None:

        self.session.add(question_result)

    async def get(self, question_id: UUID) -> QuestionResultModel | None:
        result = await self.session.execute(
            select(QuestionResultModel).where(QuestionResultModel.id == question_id)
        )

        return result.scalar_one_or_none()

    async def list_question_results(
        self,
        run_id: UUID,
    ) -> Sequence[QuestionResultModel]:
        result = await self.session.execute(
            select(QuestionResultModel).where(QuestionResultModel.run_id == run_id)
        )

        return result.scalars().all()
