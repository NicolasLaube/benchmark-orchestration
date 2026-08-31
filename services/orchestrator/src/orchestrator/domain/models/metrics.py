from dataclasses import dataclass


@dataclass(frozen=True)
class LatencyMetrics:
    p50: float | None = None
    p95: float | None = None
    min: float | None = None
    max: float | None = None


@dataclass(frozen=True)
class Metrics:
    total_requests: int
    successful_requests: int
    failure_count: int
    accuracy: float
    latency_ms: LatencyMetrics


@dataclass(frozen=True)
class BenchmarkMetrics:
    benchmark_id: str
    metrics: Metrics
