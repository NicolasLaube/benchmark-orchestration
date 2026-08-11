"""
This module defines the `ReportMetricsCollector` class, which is responsible for collecting and
summarizing metrics from benchmark test results. It provides methods to calculate various metrics
such as total requests, successful requests, failure count, accuracy, latency statistics (including
 percentiles), and throughput. The class also supports summarizing metrics on a per-benchmark basis.
"""

from collections import defaultdict
from statistics import median

from orchestrator.report.models import (
    BenchmarkMetrics,
    LatencyMetrics,
    Metrics,
    QuestionResult,
    ReportSummary,
)
from orchestrator.utils.compute_percentile import percentile


class MetricsCollector:
    def summarize(
        self,
        results: list[QuestionResult],
        total_wall_time_sec: float,
    ) -> ReportSummary:
        metrics = self._metrics(
            results,
            include_latency_range=True,
        )

        return ReportSummary(
            **metrics.model_dump(),
            total_wall_time_sec=round(
                total_wall_time_sec,
                3,
            ),
            throughput_req_s=self._safe_ratio(
                len(results),
                total_wall_time_sec,
                digits=3,
            ),
            benchmarks=self._per_benchmark_metrics(results),
        )

    def _metrics(
        self,
        results: list[QuestionResult],
        *,
        include_latency_range: bool = False,
    ) -> Metrics:
        successful = [result for result in results if result.status == "success"]

        latencies = [
            result.latency_ms for result in successful if result.latency_ms is not None
        ]

        return Metrics(
            total_requests=len(results),
            successful_requests=len(successful),
            failure_count=sum(result.status == "failed" for result in results),
            accuracy=self._safe_ratio(
                sum(bool(result.correct) for result in successful),
                len(successful),
            ),
            latency_ms=LatencyMetrics(
                p50=median(latencies) if latencies else None,
                p95=percentile(latencies, 0.95),
                min=(min(latencies) if include_latency_range and latencies else None),
                max=(max(latencies) if include_latency_range and latencies else None),
            ),
        )

    def _per_benchmark_metrics(
        self,
        results: list[QuestionResult],
    ) -> list[BenchmarkMetrics]:
        by_benchmark: dict[
            str,
            list[QuestionResult],
        ] = defaultdict(list)

        for result in results:
            by_benchmark[str(result.benchmark_id)].append(result)

        return [
            BenchmarkMetrics(
                benchmark_id=benchmark_id,
                **self._metrics(benchmark_results).model_dump(),
            )
            for benchmark_id, benchmark_results in sorted(by_benchmark.items())
        ]

    @staticmethod
    def _safe_ratio(
        numerator: float,
        denominator: float,
        *,
        digits: int = 4,
    ) -> float:
        if denominator == 0:
            return 0.0

        return round(
            numerator / denominator,
            digits,
        )
