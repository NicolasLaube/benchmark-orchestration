from typing import Self

from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table

from orchestrator.monitoring.run_metrics import RunMetrics
from orchestrator.utils.format_duration import format_duration


class RichProgressView:
    def __init__(
        self,
        metrics: RunMetrics,
        refresh_per_second: int = 4,
        console: Console | None = None,
    ) -> None:
        self.metrics = metrics
        self.console = console or Console()
        self.live = Live(
            self.render(),
            console=self.console,
            refresh_per_second=refresh_per_second,
            transient=False,
        )

    def __enter__(self) -> Self:
        self.live.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.live.__exit__(exc_type, exc, tb)

    def refresh(self) -> None:
        self.live.update(self.render())

    def render(self) -> Panel:
        metrics = self.metrics

        progress = Progress(
            TextColumn("Progress       "),
            BarColumn(bar_width=28),
            TextColumn("{task.percentage:>5.1f}%"),
            expand=False,
        )
        progress.add_task(
            "benchmark",
            total=metrics.total,
            completed=metrics.completed,
        )

        eta_text = format_duration(metrics.eta_sec())

        avg_latency = metrics.average_latency_ms()
        p50_latency = metrics.p50_latency_ms()
        p95_latency = metrics.p95_latency_ms()

        latency_text = "-"
        if (
            avg_latency is not None
            and p50_latency is not None
            and p95_latency is not None
        ):
            latency_text = f"{avg_latency:.0f} / {p50_latency} / {p95_latency} ms"

        table = Table.grid(padding=(0, 2))
        table.add_column(justify="left", style="bold")
        table.add_column(justify="right")

        table.add_row("Completed", f"{metrics.completed} / {metrics.total}")
        table.add_row("HTTP attempts", str(metrics.http_attempts))
        table.add_row(
            "Overall throughput",
            (
                f"{metrics.throughput():.2f} req/s ({metrics.throughput_rpm():.1f} req/min)"
            ),
        )
        table.add_row(
            "Recent throughput (30s)",
            (
                f"{metrics.recent_throughput():.2f} req/s "
                f"({metrics.recent_throughput_rpm():.1f} req/min)"
            ),
        )
        table.add_row("Latency avg / p50 / p95", latency_text)

        table.add_row("Target concurrency", str(metrics.target_concurrency))
        table.add_row("HTTP in-flight", str(metrics.http_in_flight))
        table.add_row("Peak HTTP in-flight", str(metrics.peak_http_in_flight))

        table.add_row("Launch RPM", f"≈ {metrics.launch_rpm}")
        table.add_row(
            "Launch interval",
            f"{metrics.launch_interval_sec:.3f}s",
        )
        table.add_row("Controller phase", str(metrics.phase))
        table.add_row(
            "Learned capacity",
            (
                f"RPM≈{metrics.estimated_rpm_limit or '-'} | "
                f"concurrency≈{metrics.estimated_concurrency_limit or '-'}"
            ),
        )

        table.add_row(
            "Rate limits",
            (
                f"{metrics.rate_limited} "
                f"(RPM {metrics.rpm_limited}, "
                f"conc {metrics.concurrency_limited}, "
                f"unknown {metrics.generic_overload})"
            ),
        )
        table.add_row("Retries", str(metrics.retries))
        table.add_row("Accuracy", f"{metrics.accuracy():.1f} %")
        table.add_row("ETA", eta_text)

        body = Group(
            Align.left(progress),
            "",
            table,
        )

        return Panel(
            body,
            title="Benchmark Orchestrator",
            border_style="cyan",
            padding=(1, 2),
        )
