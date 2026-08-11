from rich.console import Console
from rich.table import Table

from orchestrator.report.models import ReportSummary


def print_summary(
    summary: ReportSummary,
    console: Console | None = None,
) -> None:
    console = console or Console()

    table = Table(
        title="Benchmark Summary",
        show_header=True,
    )

    table.add_column("Metric")
    table.add_column("Value", justify="right")

    table.add_row(
        "Total requests",
        str(summary.total_requests),
    )

    table.add_row(
        "Successful requests",
        str(summary.successful_requests),
    )

    table.add_row(
        "Failures",
        str(summary.failure_count),
    )

    table.add_row(
        "Accuracy",
        f"{summary.accuracy * 100:.1f}%",
    )

    table.add_row(
        "Wall time",
        f"{summary.total_wall_time_sec:.2f} s",
    )

    table.add_row(
        "Throughput",
        f"{summary.throughput_req_s:.2f} req/s",
    )

    table.add_row(
        "p50 latency",
        _format_latency(summary.latency_ms.p50),
    )

    table.add_row(
        "p95 latency",
        _format_latency(summary.latency_ms.p95),
    )

    if summary.latency_ms.min is not None:
        table.add_row(
            "Min latency",
            _format_latency(summary.latency_ms.min),
        )

    if summary.latency_ms.max is not None:
        table.add_row(
            "Max latency",
            _format_latency(summary.latency_ms.max),
        )

    console.print(table)

    if summary.benchmarks:
        _print_benchmark_summary(
            summary,
            console,
        )


def _print_benchmark_summary(
    summary: ReportSummary,
    console: Console,
) -> None:
    table = Table(
        title="Per Benchmark",
        show_header=True,
    )

    table.add_column("Benchmark")
    table.add_column("Requests", justify="right")
    table.add_column("Success", justify="right")
    table.add_column("Failures", justify="right")
    table.add_column("Accuracy", justify="right")
    table.add_column("p50", justify="right")
    table.add_column("p95", justify="right")

    for benchmark in summary.benchmarks:
        table.add_row(
            benchmark.benchmark_id,
            str(benchmark.total_requests),
            str(benchmark.successful_requests),
            str(benchmark.failure_count),
            f"{benchmark.accuracy * 100:.1f}%",
            _format_latency(benchmark.latency_ms.p50),
            _format_latency(benchmark.latency_ms.p95),
        )

    console.print(table)


def _format_latency(
    latency_ms: float | None,
) -> str:
    if latency_ms is None:
        return "-"

    return f"{latency_ms:.1f} ms"
