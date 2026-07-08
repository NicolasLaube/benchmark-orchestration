import asyncio
import logging
import time

import typer

from rich.logging import RichHandler


from orchestrator.graders.grader import SubstringGrader
from orchestrator.inference_client import InferenceClient
from orchestrator.loaders.loader_benchmark import LoaderCsvBenchmark
from orchestrator.loaders.loader_queue import LoaderJsonlQueue
from orchestrator.metrics import MetricsCollector
from orchestrator.reporter import JsonReporter
from orchestrator.runner import Runner
from orchestrator.schedulers.scheduler_concurrent import FixedConcurrencyScheduler


def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                show_time=True,
                show_level=True,
                show_path=False,
            )
        ],
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)


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
    max_concurrency: int = typer.Option(
        4,
        help="Maximum orchestrator-side concurrency.",
    ),
    max_retries: int = typer.Option(
        3,
        help="Maximum retries per question.",
    ),
    log_level: str = typer.Option(
        "INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    ),
    progress_every: int = typer.Option(
        10,
        help="Log progress every N completed requests.",
    ),
) -> None:
    async def _run() -> None:
        async with InferenceClient(
            endpoint=endpoint,
            timeout_sec=timeout_sec,
        ) as inference_client:
            configure_logging(log_level)
            runner = Runner(
                loader_benchmark=LoaderCsvBenchmark(),
                loader_queue=LoaderJsonlQueue(),
                scheduler=FixedConcurrencyScheduler(
                    inference_client=inference_client,
                    grader=SubstringGrader(),
                    max_concurrency=max_concurrency,
                    max_retries=max_retries,
                    progress_every=progress_every,
                ),
            )

            start = time.perf_counter()
            results = await runner.run(queue_path=queue)
            total_wall_time_sec = time.perf_counter() - start

        summary = MetricsCollector().summarize(
            results=results,
            total_wall_time_sec=total_wall_time_sec,
        )

        JsonReporter().write(
            output_path=out,
            summary=summary,
            results=results,
        )

        typer.echo(f"Completed {summary['total_requests']} requests")
        typer.echo(f"Successful: {summary['successful_requests']}")
        typer.echo(f"Failures: {summary['failure_count']}")
        typer.echo(f"Accuracy: {summary['accuracy']}")
        typer.echo(f"Results written to {out}")

    asyncio.run(_run())


def app_cli() -> None:
    typer.run(run_benchmark)


if __name__ == "__main__":
    app_cli()
