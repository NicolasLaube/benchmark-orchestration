import asyncio
import time

import typer
from orchestrator.loaders.loader_queue import LoaderJsonlQueue

from orchestrator.loaders.loader_benchmark import LoaderCsvBenchmark
from orchestrator.graders.grader import SubstringGrader
from orchestrator.inference_client import InferenceClient
from orchestrator.metrics import MetricsCollector
from orchestrator.reporter import JsonReporter
from orchestrator.runner import Runner


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
) -> None:
    async def _run() -> None:
        async with InferenceClient(
            endpoint=endpoint,
            timeout_sec=timeout_sec,
        ) as inference_client:
            runner = Runner(
                benchmark_loader=LoaderCsvBenchmark(),
                queue_loader=LoaderJsonlQueue(),
                grader=SubstringGrader(),
                inference_client=inference_client,
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