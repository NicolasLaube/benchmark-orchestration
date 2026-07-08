from orchestrator.graders.grader import SubstringGrader
from orchestrator.inference_client import InferenceClient, InferenceClientError
from orchestrator.models import BenchmarkQuestion, QuestionResult


class SequentialScheduler:
    def __init__(
        self,
        inference_client: InferenceClient,
        grader: SubstringGrader,
    ) -> None:
        self.inference_client = inference_client
        self.grader = grader

    async def run_questions(
        self,
        questions: list[BenchmarkQuestion],
    ) -> list[QuestionResult]:
        results: list[QuestionResult] = []

        for question in questions:
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
