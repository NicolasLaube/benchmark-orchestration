import asyncio
import json
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from orchestrator.application.build_report import build_report
from orchestrator.application.config import (
    RunConfig,
    SchedulerMode,
    Settings,
)
from orchestrator.application.run_benchmark import (
    execute_benchmark,
)
from orchestrator.domain.models.question import BenchmarkQuestion
from orchestrator.domain.scheduling.aimd.config import AdaptiveAimdSchedulerConfig
from orchestrator.domain.scheduling.fixed.config import FixedConcurrencySchedulerConfig
from orchestrator.infrastructure.persistence.db import SessionLocal
from orchestrator.infrastructure.persistence.models.runs import RunModel
from orchestrator.infrastructure.persistence.repositories.report import (
    RunReportRepository,
)
from orchestrator.infrastructure.persistence.repositories.run import RunRepository
from orchestrator.interfaces.api.auth.auth import verify_access_token
from orchestrator.interfaces.api.load import load_questions_from_upload

runs_router = APIRouter(
    prefix="/runs",
    dependencies=[Depends(verify_access_token)],
)


@runs_router.post("", tags=["runs"])
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
) -> dict:

    questions = await load_questions_from_upload(file)

    async with SessionLocal() as session:
        repo = RunRepository(session=session)

        run_id = uuid4()

        await repo.create(
            RunModel(
                id=run_id,
                status="queued",
                total=len(questions),
                completed=0,
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
        "status": "queued",
    }


@runs_router.get("/{run_id}")
async def get_state(run_id: UUID):
    async with SessionLocal() as session:
        repo = RunRepository(session=session)

        run = await repo.get(run_id)

        if run is None:
            raise HTTPException(
                status_code=404,
                detail=f"The run {run_id} doesn't exist",
            )

        return run


@runs_router.get("/{run_id}/report")
async def get_report(run_id: UUID):
    async with SessionLocal() as session:
        repo = RunRepository(session=session)
        report_repo = RunReportRepository(session=session)

        run = await repo.get(run_id)

        if run is None:
            raise HTTPException(
                status_code=404,
                detail=f"The run {run_id} doesn't exist",
            )

        if run.status != "finished":
            raise HTTPException(
                status_code=409,
                detail=f"The run {run_id} didn't finish yet",
            )

        report = await report_repo.get(run_id)

        session.commit()

        if report is None:
            await build_report(run_id)
            report = await report_repo.get(run_id)

            session.commit()

        return report.report


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
    async with SessionLocal() as session:
        repo = RunRepository(session)

        run = await repo.get(run_id)

        if run is None:
            raise HTTPException(
                status_code=404,
                detail=f"The run {run_id} doesn't exist",
            )

    async def event_generator():
        while True:
            async with SessionLocal() as session:
                repo = RunRepository(session)

                run = await repo.get(run_id)

            if run is None:
                break

            payload = {
                "run_id": str(run.id),
                "status": run.status,
                "completed": run.completed,
                "total": run.total,
            }

            yield f"data: {json.dumps(payload)}\n\n"

            if run.status in {"finished", "failed"}:
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

    await execute_benchmark(
        config=config,
        settings=Settings(),
        questions=questions,
        run_id=run_id,
    )

    # run_store.update_report(run_id=run_id, report=report)
