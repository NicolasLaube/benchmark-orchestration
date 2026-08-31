import asyncio
from typing import Annotated
from uuid import uuid4

import typer
from orchestrator.application.build_report import build_report
from orchestrator.application.config import (
    RunConfig,
    SchedulerMode,
    Settings,
)
from orchestrator.application.run_benchmark import execute_benchmark
from orchestrator.domain.scheduling.aimd.config import AdaptiveAimdSchedulerConfig
from orchestrator.domain.scheduling.fixed.config import FixedConcurrencySchedulerConfig
from orchestrator.infrastructure.io.load_questions import load_questions
from orchestrator.interfaces.cli.json_reporter import JsonReporter
from orchestrator.interfaces.cli.rich_summary import print_summary


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
    run_id = uuid4()

    asyncio.run(
        execute_benchmark(
            config=config,
            settings=settings,
            questions=questions,
            run_id=run_id,
        )
    )

    report = asyncio.run(build_report(run_id))

    print_summary(report.summary)

    JsonReporter().write(
        output_path="results/report.json",
        report=report,
    )


def app_cli() -> None:
    typer.run(run_benchmark)


if __name__ == "__main__":
    app_cli()
