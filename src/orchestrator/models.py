
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class BenchmarkJob:
    id: str
    path: str

@dataclass(frozen=True)
class BenchmarkQuestion:
    benchmark_id: str
    question_id: str
    question: str
    expected_answer: str
@dataclass(frozen=True)
class InferenceResult:
    answer: str
    model: str
    latency_ms: int


@dataclass(frozen=True)
class GradeResult:
    correct: bool
    score: float


@dataclass(frozen=True)
class QuestionResult:
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