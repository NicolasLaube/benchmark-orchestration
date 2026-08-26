from uuid import UUID

from orchestrator.persistence.models import QuestionResultModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class QuestionResultRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, question_result: QuestionResultModel) -> None:

        self.session.add(question_result)

        await self.session.commit()

    async def get(self, question_id: UUID) -> QuestionResultModel | None:
        result = await self.session.execute(
            select(QuestionResultModel).where(QuestionResultModel.id == question_id)
        )

        return result.scalar_one_or_none()
