"""
This module defines the `ReportMetricsCollector` class, which is responsible for collecting and
summarizing metrics from benchmark test results. It provides methods to calculate various metrics
such as total requests, successful requests, failure count, accuracy, latency statistics (including
 percentiles), and throughput. The class also supports summarizing metrics on a per-benchmark basis.
"""

from collections import defaultdict
from statistics import median

from orchestrator.report.models import QuestionResult
from orchestrator.utils.compute_percentile import percentile


class ReportMetricsCollector:
    def summarize(
        self,
        results: list[QuestionResult],
        total_wall_time_sec: float,
    ) -> dict:
        return {
            "total_wall_time_sec": round(total_wall_time_sec, 3),
            **self._metrics(results, include_latency_range=True),
            "throughput_req_s": self._safe_ratio(
                len(results),
                total_wall_time_sec,
                digits=3,
            ),
            "benchmarks": self._per_benchmark_metrics(results),
        }

    def _metrics(
        self,
        results: list[QuestionResult],
        *,
        include_latency_range: bool = False,
    ) -> dict:
        successful = [r for r in results if r.status == "success"]
        latencies = [r.latency_ms for r in successful if r.latency_ms is not None]

        latency_metrics = {
            "p50": median(latencies) if latencies else None,
            "p95": percentile(latencies, 0.95),
        }

        if include_latency_range:
            latency_metrics |= {
                "min": min(latencies) if latencies else None,
                "max": max(latencies) if latencies else None,
            }

        return {
            "total_requests": len(results),
            "successful_requests": len(successful),
            "failure_count": sum(r.status == "failed" for r in results),
            "accuracy": self._safe_ratio(
                sum(bool(r.correct) for r in successful),
                len(successful),
            ),
            "latency_ms": latency_metrics,
        }

    def _per_benchmark_metrics(
        self,
        results: list[QuestionResult],
    ) -> list[dict]:
        by_benchmark: dict[str, list[QuestionResult]] = defaultdict(list)

        for result in results:
            by_benchmark[result.benchmark_id].append(result)

        return [
            {
                "benchmark_id": benchmark_id,
                **self._metrics(benchmark_results),
            }
            for benchmark_id, benchmark_results in sorted(by_benchmark.items())
        ]

    @staticmethod
    def _safe_ratio(
        numerator: float,
        denominator: float,
        *,
        digits: int = 4,
    ) -> float:
        return round(numerator / denominator, digits) if denominator else 0.0
