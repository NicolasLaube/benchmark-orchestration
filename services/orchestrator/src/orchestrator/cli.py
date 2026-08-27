import asyncio
from typing import Annotated
from uuid import uuid4

import typer

from orchestrator.application.config import (
    RunConfig,
    SchedulerMode,
    Settings,
)
from orchestrator.application.run_benchmark import execute_benchmark
from orchestrator.io.load_questions import load_questions
from orchestrator.monitoring.rich_summary import print_summary
from orchestrator.report.writer import JsonReporter
from orchestrator.schedulers.aimd.config import AdaptiveAimdSchedulerConfig
from orchestrator.schedulers.fixed.config import FixedConcurrencySchedulerConfig


def run_benchmark(
    queue: str = typer.Option(
        "data/queue_smoke.jsonl",
    ),
    scheduler_mode: Annotated[
        SchedulerMode,
        typer.Option(
            "--scheduler",
            help="Scheduler strategy: fixed or aimd.",
        ),
    ] = SchedulerMode.AIMD,
    max_concurrency: int = typer.Option(4),
    max_target_concurrency: int = typer.Option(32),
    max_retries: int = typer.Option(3),
) -> None:
    if scheduler_mode == SchedulerMode.AIMD:
        scheduler_config = AdaptiveAimdSchedulerConfig(
            initial_concurrency=max_concurrency,
            max_target_concurrency=(max_target_concurrency),
            max_retries=max_retries,
        )

    else:
        scheduler_config = FixedConcurrencySchedulerConfig(
            max_concurrency=max_concurrency,
            max_retries=max_retries,
        )

    config = RunConfig(
        scheduler=scheduler_config,
    )

    settings = Settings()

    questions = load_questions(queue)

    report = asyncio.run(
        execute_benchmark(
            config=config, settings=settings, questions=questions, run_id=uuid4()
        )
    )

    print_summary(report.summary)

    JsonReporter().write(
        output_path="results/report.json",
        report=report,
    )


def app_cli() -> None:
    typer.run(run_benchmark)


if __name__ == "__main__":
    app_cli()
