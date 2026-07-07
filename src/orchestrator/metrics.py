from collections import defaultdict
from statistics import median

from orchestrator.models import QuestionResult


def percentile(values: list[int], p: float) -> float | None:
    if not values:
        return None

    sorted_values = sorted(values)

    if len(sorted_values) == 1:
        return float(sorted_values[0])

    index = int(round((len(sorted_values) - 1) * p))
    return float(sorted_values[index])


class MetricsCollector:
    def summarize(
        self,
        results: list[QuestionResult],
        total_wall_time_sec: float,
    ) -> dict:
        return {
            "total_wall_time_sec": round(total_wall_time_sec, 3),
            **self._global_metrics(results, total_wall_time_sec),
            "benchmarks": self._per_benchmark_metrics(results),
        }

    def _global_metrics(
        self,
        results: list[QuestionResult],
        total_wall_time_sec: float,
    ) -> dict:
        total_requests = len(results)

        successful_results = [result for result in results if result.status == "success"]
        failed_results = [result for result in results if result.status == "failed"]
        correct_results = [result for result in successful_results if result.correct]

        latencies = [
            result.latency_ms for result in successful_results if result.latency_ms is not None
        ]

        successful_requests = len(successful_results)
        failure_count = len(failed_results)

        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failure_count": failure_count,
            "accuracy": self._safe_ratio(len(correct_results), successful_requests),
            "throughput_req_s": (
                round(total_requests / total_wall_time_sec, 3) if total_wall_time_sec > 0 else 0.0
            ),
            "latency_ms": {
                "p50": median(latencies) if latencies else None,
                "p95": percentile(latencies, 0.95),
                "min": min(latencies) if latencies else None,
                "max": max(latencies) if latencies else None,
            },
        }

    def _per_benchmark_metrics(
        self,
        results: list[QuestionResult],
    ) -> list[dict]:
        by_benchmark: dict[str, list[QuestionResult]] = defaultdict(list)

        for result in results:
            by_benchmark[result.benchmark_id].append(result)

        benchmark_metrics: list[dict] = []

        for benchmark_id, benchmark_results in sorted(by_benchmark.items()):
            successful_results = [
                result for result in benchmark_results if result.status == "success"
            ]
            failed_results = [result for result in benchmark_results if result.status == "failed"]
            correct_results = [result for result in successful_results if result.correct]

            latencies = [
                result.latency_ms for result in successful_results if result.latency_ms is not None
            ]

            successful_requests = len(successful_results)

            benchmark_metrics.append(
                {
                    "benchmark_id": benchmark_id,
                    "total_requests": len(benchmark_results),
                    "successful_requests": successful_requests,
                    "failure_count": len(failed_results),
                    "accuracy": self._safe_ratio(
                        len(correct_results),
                        successful_requests,
                    ),
                    "latency_ms": {
                        "p50": median(latencies) if latencies else None,
                        "p95": percentile(latencies, 0.95),
                    },
                }
            )

        return benchmark_metrics

    def _safe_ratio(self, numerator: int, denominator: int) -> float:
        if denominator == 0:
            return 0.0

        return round(numerator / denominator, 4)
