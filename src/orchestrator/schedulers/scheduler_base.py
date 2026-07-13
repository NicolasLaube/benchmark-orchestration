from typing import Protocol

from orchestrator.report.report_models import QuestionResult
from orchestrator.loaders.loader_benchmark import BenchmarkQuestion


class Scheduler(Protocol):
    async def run_questions(
        self,
        questions: list[BenchmarkQuestion],
    ) -> list[QuestionResult]: ...
