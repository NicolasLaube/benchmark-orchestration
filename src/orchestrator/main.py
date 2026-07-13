import asyncio
import time
from enum import StrEnum

import typer
from rich.console import Console

from orchestrator.graders.grader import SubstringGrader
from orchestrator.inference_client.inference_client import InferenceClient
from orchestrator.loaders.loader_benchmark import LoaderCsvBenchmark
from orchestrator.loaders.loader_queue import LoaderJsonlQueue
from orchestrator.monitoring import RichProgressView, configure_logging
from orchestrator.report.report_json_saver import JsonReporter
from orchestrator.report.report_metrics_collector import ReportMetricsCollector
from orchestrator.runner import Runner
from orchestrator.schedulers.scheduler_aimd_v3 import AdaptiveAimdConfig, AdaptiveAimdScheduler
from orchestrator.schedulers.scheduler_fixed_v2 import (
    FixedConcurrencyConfig,
    FixedConcurrencyScheduler,
)


class SchedulerMode(StrEnum):
    FIXED = "fixed"
    AIMD = "aimd"


def run_benchmark(
    queue: str = typer.Option(
        "data/queue_smoke.jsonl",
        help="Path to the benchmark queue JSONL file.",
    ),
    endpoint: str = typer.Option(
        "http://localhost:8000/infer",
        help="Inference service endpoint.",
    ),
    out: str = typer.Option(
        "results/smoke.json",
        help="Path to the output results JSON file.",
    ),
    timeout_sec: float = typer.Option(
        120.0,
        help="HTTP timeout in seconds.",
    ),
    max_retries: int = typer.Option(
        3,
        help="Maximum retries per question.",
    ),
    log_level: str = typer.Option(
        "INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    ),
    scheduler_mode: SchedulerMode = typer.Option(  # noqa: B008
        SchedulerMode.AIMD,
        "--scheduler",
        help="Scheduler strategy: fixed or aimd.",
    ),
    max_concurrency: int = typer.Option(
        4,
        help="Concurrency used by the fixed scheduler.",
    ),
    max_target_concurrency: int = typer.Option(
        32,
        help="Safety ceiling used by the adaptive AIMD scheduler.",
    ),
    progress_log_every: int | None = typer.Option(
        None,
        help="Log progress every N questions. None disables periodic logs.",
    ),
    show_progress: bool = typer.Option(
        True,
        help="Show rich progress view during benchmark run.",
    ),
) -> None:

    console = Console()

    scheduler_logger = configure_logging(
        log_level=log_level,
        console=console,
    )

    def progress_view_factory(metrics):
        return (
            RichProgressView(
                metrics=metrics,
                console=console,
            )
            if show_progress
            else None
        )

    async def _run() -> None:
        async with InferenceClient(
            endpoint=endpoint,
            timeout_sec=timeout_sec,
        ) as inference_client:
            common_scheduler_kwargs = {
                "inference_client": inference_client,
                "grader": SubstringGrader(),
                "logger": scheduler_logger,
                "console": console,
                "progress_view_factory": progress_view_factory,
            }

            if scheduler_mode == SchedulerMode.FIXED:
                scheduler = FixedConcurrencyScheduler(
                    **common_scheduler_kwargs,
                    config=FixedConcurrencyConfig(
                        max_concurrency=max_concurrency,
                        max_retries=max_retries,
                        progress_log_every=progress_log_every,
                    ),
                )

            else:
                scheduler = AdaptiveAimdScheduler(
                    **common_scheduler_kwargs,
                    config=AdaptiveAimdConfig(
                        initial_concurrency=1,
                        max_target_concurrency=max_target_concurrency,
                        max_retries=max_retries,
                        progress_log_every=progress_log_every,
                    ),
                )

            runner = Runner(
                loader_benchmark=LoaderCsvBenchmark(),
                loader_queue=LoaderJsonlQueue(),
                scheduler=scheduler,
            )

            start = time.perf_counter()

            results = await runner.run(queue_path=queue)

            total_wall_time_sec = time.perf_counter() - start

        summary = ReportMetricsCollector().summarize(
            results=results,
            total_wall_time_sec=total_wall_time_sec,
        )

        JsonReporter().write(
            output_path=out,
            summary=summary,
            results=results,
        )

    asyncio.run(_run())


def app_cli() -> None:
    typer.run(run_benchmark)


if __name__ == "__main__":
    app_cli()
