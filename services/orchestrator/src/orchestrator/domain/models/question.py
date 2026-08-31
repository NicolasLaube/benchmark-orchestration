from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkQuestion:
    """Represents a single benchmark question with its associated metadata."""

    benchmark_id: str
    question_id: str
    question: str
    expected_answer: str
