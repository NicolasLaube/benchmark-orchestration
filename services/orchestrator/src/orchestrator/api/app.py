from fastapi import FastAPI
from orchestrator.api.schemas import RunRequest
from orchestrator.application.config import (
    RunConfig,
    SchedulerMode,
    Settings,
)
from orchestrator.application.run_benchmark import (
    execute_benchmark,
)
from orchestrator.io.load_questions import load_questions
from orchestrator.schedulers.aimd.config import AdaptiveAimdSchedulerConfig
from orchestrator.schedulers.fixed.config import FixedConcurrencySchedulerConfig


def create_app() -> FastAPI:
    app = FastAPI(
        title="Benchmark Orchestrator",
        version="0.1.0",
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/runs")
    async def create_run(
        request: RunRequest,
    ):
        questions = load_questions(request.queue_path)

        if request.scheduler == SchedulerMode.AIMD:
            scheduler_config = AdaptiveAimdSchedulerConfig(
                initial_concurrency=(request.max_concurrency),
                max_target_concurrency=(request.max_target_concurrency),
                max_retries=request.max_retries,
            )
        else:
            scheduler_config = FixedConcurrencySchedulerConfig(
                max_concurrency=(request.max_concurrency),
                max_retries=request.max_retries,
            )

        config = RunConfig(
            scheduler=scheduler_config,
        )

        settings = Settings()

        report = await execute_benchmark(
            config=config,
            settings=settings,
            questions=questions,
        )

        return report

    return app


app = create_app()
