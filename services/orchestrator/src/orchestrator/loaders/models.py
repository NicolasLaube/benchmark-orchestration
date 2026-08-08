"""
This module defines data models for benchmark jobs and questions used in the orchestrator.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkJob:
    """Represents a benchmark job with its associated metadata."""

    id: str
    path: str


@dataclass(frozen=True)
class BenchmarkQuestion:
    """Represents a single benchmark question with its associated metadata."""

    benchmark_id: str
    question_id: str
    question: str
    expected_answer: str
