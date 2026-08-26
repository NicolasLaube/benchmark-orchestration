import asyncio
import json
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from orchestrator.api.load import load_questions_from_upload
from orchestrator.api.store import RunState, RunStatus, run_store
from orchestrator.application.config import (
    RunConfig,
    SchedulerMode,
    Settings,
)
from orchestrator.application.run_benchmark import (
    execute_benchmark,
)
from orchestrator.io.models import BenchmarkQuestion
from orchestrator.report.models import BenchmarkReport
from orchestrator.schedulers.aimd.config import AdaptiveAimdSchedulerConfig
from orchestrator.schedulers.fixed.config import FixedConcurrencySchedulerConfig

runs_router = APIRouter(prefix="/runs")


@runs_router.post("/", tags=["runs"])
async def create_run(
    file: Annotated[
        UploadFile,
        File(),
    ],
    scheduler: Annotated[
        SchedulerMode,
        Form(),
    ] = SchedulerMode.AIMD,
    max_concurrency: Annotated[
        int,
        Form(),
    ] = 4,
    max_target_concurrency: Annotated[
        int,
        Form(),
    ] = 32,
    max_retries: Annotated[
        int,
        Form(),
    ] = 3,
):
    run_id = uuid4()

    questions = await load_questions_from_upload(file)

    run_store.create(
        RunState(
            run_id=run_id,
            total=len(questions),
            completed=0,
            report=None,
            status=RunStatus.queued,
        )
    )

    asyncio.create_task(
        run_benchmark(
            run_id=run_id,
            questions=questions,
            max_concurrency=max_concurrency,
            max_retries=max_retries,
            max_target_concurrency=max_target_concurrency,
            scheduler=scheduler,
        )
    )

    return {
        "run_id": run_id,
        "status": RunStatus.queued,
    }


@runs_router.get("/{run_id}")
async def get_state(run_id: UUID):
    run_state: RunState = run_store.get(run_id)

    if run_state is None:
        raise HTTPException(
            status_code=404,
            detail=f"The run {run_id} doesn't exist",
        )

    return run_store.get(run_id=run_id)


@runs_router.get("/{run_id}/report")
async def get_report(run_id: UUID):
    run_state: RunState = run_store.get(run_id)

    if run_state is None:
        raise HTTPException(
            status_code=404,
            detail=f"The run {run_id} doesn't exist",
        )

    if run_state.status != RunStatus.finished:
        raise HTTPException(
            status_code=409,
            detail=f"The run {run_id} didn't finish yet",
        )

    return run_store.get(run_id=run_id).report


@runs_router.get(
    "/{run_id}/events",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": "Stream run progress using Server-Sent Events",
        }
    },
)
async def get_events(run_id: UUID) -> StreamingResponse:
    run = run_store.get(run_id=run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail=f"The run {run_id} doesn't exist",
        )

    async def event_generator():
        run = run_store.get(run_id=run_id)

        while True:
            payload = {
                "run_id": str(run.run_id),
                "status": run.status.value,
                "completed": run.completed,
                "total": run.total,
            }

            yield f"data: {json.dumps(payload)}\n\n"

            if run.status in {
                RunStatus.finished,
                RunStatus.failed,
            }:
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


async def run_benchmark(
    run_id: UUID,
    questions: list[BenchmarkQuestion],
    scheduler: SchedulerMode,
    max_concurrency: int,
    max_target_concurrency: int,
    max_retries: int,
):
    if scheduler == SchedulerMode.AIMD:
        scheduler_config = AdaptiveAimdSchedulerConfig(
            initial_concurrency=max_concurrency,
            max_target_concurrency=max_target_concurrency,
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

    report: BenchmarkReport = await execute_benchmark(
        config=config,
        settings=Settings(),
        questions=questions,
    )

    run_store.update_report(run_id=run_id, report=report)
