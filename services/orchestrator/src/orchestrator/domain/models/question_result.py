from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class QuestionResult:
    """Represents the result of a single question in a benchmark test."""

    benchmark_id: str
    question_id: str
    question: str
    expected_answer: str

    answer: str | None
    correct: bool
    score: float

    latency_ms: int | None
    attempts: int
    status: Literal["success", "failed"]
    error: str | None = None
