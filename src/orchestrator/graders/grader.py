# The grader is responsible for running the grading logic.
# For example, for "What is the capital of France?", the grader will check if the answer is "Paris".
# if the answer is correct, the grader will return a score of 1. If the answer is incorrect, the
# grader will return a score of 0.


from orchestrator.models import GradeResult


class SubstringGrader:
    def grade(self, answer: str, expected_answer: str) -> GradeResult:
        correct = expected_answer.strip().lower() in answer.strip().lower()

        return GradeResult(
            correct=correct,
            score=1.0 if correct else 0.0,
        )
