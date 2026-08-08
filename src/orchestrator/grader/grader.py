"""
The FGrader module provides a simple grading mechanism for evaluating the correctness of answers
based on substring matching. It checks if the expected answer is present as a substring in the
actual answer provided. The grading is case-insensitive and ignores leading and trailing whitespace.
"""

from orchestrator.grader.grader_models import GradeResult


class SubstringGrader:
    def grade(self, answer: str, expected_answer: str) -> GradeResult:
        """
        Grades the given answer against the expected answer using substring matching.

        Args:
            answer (str): The answer to be graded.
            expected_answer (str): The expected answer.

        Returns:
            GradeResult: The result of the grading, including correctness and score.
        """
        correct = expected_answer.strip().lower() in answer.strip().lower()

        return GradeResult(
            correct=correct,
            score=1.0 if correct else 0.0,
        )
