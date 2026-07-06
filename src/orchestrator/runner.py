import time

from orchestrator.loaders.loader_benchmark import LoaderCsvBenchmark
from orchestrator.loaders.loader_queue import LoaderJsonlQueue
from orchestrator.inference_client import InferenceClient, InferenceClientError
from orchestrator.models import BenchmarkQuestion, QuestionResult
from orchestrator.graders.grader import SubstringGrader

class Runner:
    def __init__(
        self,
        queue_loader: LoaderJsonlQueue,
        benchmark_loader: LoaderCsvBenchmark,
        inference_client: InferenceClient,
        grader: SubstringGrader,
    ) -> None:
        self.queue_loader = queue_loader
        self.benchmark_loader = benchmark_loader
        self.inference_client = inference_client
        self.grader = grader

    async def run(self, queue_path: str) -> list[QuestionResult]:
        jobs = self.queue_loader.load(queue_path)

        all_questions: list[BenchmarkQuestion] = []

        for job in jobs:
            questions = self.benchmark_loader.load(job)
            all_questions.extend(questions)
            # TODO: 

        results: list[QuestionResult] = []

        for question in all_questions:
            result = await self._run_one(question)
            results.append(result)

        return results

    async def _run_one(self, question: BenchmarkQuestion) -> QuestionResult:
        try:
            inference_result = await self.inference_client.infer(question.question)

            grade_result = self.grader.grade(
                answer=inference_result.answer,
                expected_answer=question.expected_answer,
            )

            return QuestionResult(
                benchmark_id=question.benchmark_id,
                question_id=question.question_id,
                question=question.question,
                expected_answer=question.expected_answer,
                answer=inference_result.answer,
                correct=grade_result.correct,
                score=grade_result.score,
                latency_ms=inference_result.latency_ms,
                attempts=1,
                status="success",
                error=None,
            )

        except InferenceClientError as exc:
            return QuestionResult(
                benchmark_id=question.benchmark_id,
                question_id=question.question_id,
                question=question.question,
                expected_answer=question.expected_answer,
                answer=None,
                correct=False,
                score=0.0,
                latency_ms=None,
                attempts=1,
                status="failed",
                error=str(exc),
            )