"""
This module defines the `QuestionResult` data class, which represents the result of a single
question in a benchmark test. It includes information about the benchmark, the question, the
expected and actual answers, correctness, score, latency, number of attempts, status, and any
error messages.
"""

from dataclasses import dataclass
from datetime import datetime

from orchestrator.domain.models.metrics import BenchmarkMetrics, Metrics
from pydantic import BaseModel


@dataclass(frozen=True)
class ReportSummary(Metrics):
    total_wall_time_sec: float
    throughput_req_s: float
    benchmarks: list[BenchmarkMetrics]


@dataclass(frozen=True)
class BenchmarkReport(BaseModel):
    generated_at: datetime
    summary: ReportSummary
