"""
This module defines the `QuestionResult` data class, which represents the result of a single
question in a benchmark test. It includes information about the benchmark, the question, the
expected and actual answers, correctness, score, latency, number of attempts, status, and any
error messages.
"""

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
