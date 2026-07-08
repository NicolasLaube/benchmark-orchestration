# tests/test_grader.py

from orchestrator.graders.grader import SubstringGrader


def test_substring_grader_is_case_insensitive() -> None:
    grader = SubstringGrader()

    result = grader.grade(
        answer="The capital of France is Paris.",
        expected_answer="paris",
    )

    assert result.correct is True
    assert result.score == 1.0


def test_substring_grader_returns_false_when_expected_missing() -> None:
    grader = SubstringGrader()

    result = grader.grade(
        answer="London",
        expected_answer="Paris",
    )

    assert result.correct is False
    assert result.score == 0.0
