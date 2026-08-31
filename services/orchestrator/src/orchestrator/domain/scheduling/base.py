from typing import Protocol

from orchestrator.infrastructure.io.benchmark import BenchmarkQuestion
from orchestrator.interfaces.api.schemas.report import QuestionResult


class Scheduler(Protocol):
    async def run_questions(
        self,
        questions: list[BenchmarkQuestion],
    ) -> list[QuestionResult]: ...
