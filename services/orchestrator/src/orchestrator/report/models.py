"""
This module defines the `QuestionResult` data class, which represents the result of a single
question in a benchmark test. It includes information about the benchmark, the question, the
expected and actual answers, correctness, score, latency, number of attempts, status, and any
error messages.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


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


class LatencyMetrics(BaseModel):
    p50: float | None = None
    p95: float | None = None
    min: float | None = None
    max: float | None = None


class Metrics(BaseModel):
    total_requests: int
    successful_requests: int
    failure_count: int
    accuracy: float
    latency_ms: LatencyMetrics


class BenchmarkMetrics(Metrics):
    benchmark_id: str


class ReportSummary(Metrics):
    total_wall_time_sec: float
    throughput_req_s: float
    benchmarks: list[BenchmarkMetrics]


class BenchmarkReport(BaseModel):
    generated_at: datetime
    summary: ReportSummary
    results: list[QuestionResult]
