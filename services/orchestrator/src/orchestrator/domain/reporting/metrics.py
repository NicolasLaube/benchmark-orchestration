from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import median

from orchestrator.domain.models.metrics import BenchmarkMetrics, LatencyMetrics, Metrics
from orchestrator.utils.compute_percentile import percentile


@dataclass
class MetricResult:
    correct: bool
    latency_ms: float | None
    error: str | None
    attempts: int
    benchmark_id: str


def compute_metrics(
    results: Sequence[MetricResult],
    *,
    include_latency_range: bool = False,
) -> Metrics:
    successful = [result for result in results if result.correct]

    latencies = [
        result.latency_ms for result in successful if result.latency_ms is not None
    ]

    return Metrics(
        total_requests=len(results),
        successful_requests=len(successful),
        failure_count=sum(result.error is not None for result in results),
        accuracy=safe_ratio(
            sum(result.correct for result in successful),
            len(successful),
        ),
        latency_ms=LatencyMetrics(
            p50=median(latencies) if latencies else None,
            p95=percentile(latencies, 0.95),
            min=min(latencies) if include_latency_range and latencies else None,
            max=max(latencies) if include_latency_range and latencies else None,
        ),
    )


def compute_per_benchmark_metrics(
    results: Sequence[MetricResult],
) -> list[BenchmarkMetrics]:
    by_benchmark: dict[str, list[MetricResult]] = defaultdict(list)

    for result in results:
        by_benchmark[result.benchmark_id].append(result)

    return [
        BenchmarkMetrics(
            benchmark_id=benchmark_id,
            metrics=compute_metrics(benchmark_results),
        )
        for benchmark_id, benchmark_results in sorted(by_benchmark.items())
    ]


def safe_ratio(
    numerator: float,
    denominator: float,
    *,
    digits: int = 4,
) -> float:
    if denominator == 0:
        return 0.0

    return round(numerator / denominator, digits)
