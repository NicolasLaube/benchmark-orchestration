from typing import Protocol

from orchestrator.models import BenchmarkQuestion, QuestionResult


class Scheduler(Protocol):
    async def run_questions(
        self,
        questions: list[BenchmarkQuestion],
    ) -> list[QuestionResult]: ...
