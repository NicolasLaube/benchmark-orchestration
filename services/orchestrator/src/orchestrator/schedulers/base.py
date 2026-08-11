from typing import Protocol

from orchestrator.io.benchmark import BenchmarkQuestion
from orchestrator.report.models import QuestionResult


class Scheduler(Protocol):
    async def run_questions(
        self,
        questions: list[BenchmarkQuestion],
    ) -> list[QuestionResult]: ...
