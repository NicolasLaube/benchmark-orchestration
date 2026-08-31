from datetime import UTC, datetime
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from orchestrator.domain.models.metrics import (
    BenchmarkMetrics as ApiBenchmarkMetrics,
)
from orchestrator.domain.models.metrics import (
    LatencyMetrics as ApiLatencyMetrics,
)
from orchestrator.domain.models.metrics import (
    Metrics as ApiMetrics,
)
from orchestrator.domain.reporting.metrics import (
    MetricResult,
    compute_metrics,
    compute_per_benchmark_metrics,
    safe_ratio,
)
from orchestrator.infrastructure.persistence.db import SessionLocal
from orchestrator.infrastructure.persistence.models import QuestionResultModel, RunModel
from orchestrator.infrastructure.persistence.repositories.question_result import (
    QuestionResultRepository,
)
from orchestrator.infrastructure.persistence.repositories.report import (
    RunReportRepository,
)
from orchestrator.infrastructure.persistence.repositories.run import RunRepository
from orchestrator.interfaces.api.schemas.report import BenchmarkReport, ReportSummary


class RunNotFoundError(ValueError):
    """Raised when a run cannot be found."""


async def build_report(run_id: UUID):

    async with SessionLocal() as session:
        run_repository = RunRepository(session)
        question_repo = QuestionResultRepository(session=session)
        report_repository = RunReportRepository(session)

        run = await run_repository.get(run_id)

        if run is None:
            raise RunNotFoundError(run_id)

        results = await question_repo.list_question_results(run_id)

        report = await assemble_report(run, results)

        await report_repository.save(
            run_id=run_id,
            report=jsonable_encoder(report),
            generated_at=report.generated_at,
        )

        await session.commit()


async def assemble_report(
    run: RunModel, results: list[QuestionResultModel]
) -> BenchmarkReport:

    metric_results = [
        MetricResult(
            correct=result.success,
            latency_ms=result.latency_ms,
            error=result.error,
            attempts=result.attempts,
            benchmark_id=result.run_id,
        )
        for result in results
    ]

    metrics = compute_metrics(
        metric_results,
        include_latency_range=True,
    )

    benchmark_metrics = compute_per_benchmark_metrics(metric_results)

    wall_time = (run.finished_at - run.started_at).total_seconds()

    summary = ReportSummary(
        total_requests=metrics.total_requests,
        successful_requests=metrics.successful_requests,
        failure_count=metrics.failure_count,
        accuracy=metrics.accuracy,
        latency_ms=ApiLatencyMetrics(
            p50=metrics.latency_ms.p50,
            p95=metrics.latency_ms.p95,
            min=metrics.latency_ms.min,
            max=metrics.latency_ms.max,
        ),
        total_wall_time_sec=round(wall_time, 3),
        throughput_req_s=safe_ratio(
            len(results),
            wall_time,
            digits=3,
        ),
        benchmarks=[
            ApiBenchmarkMetrics(
                benchmark_id=item.benchmark_id,
                metrics=ApiMetrics(
                    total_requests=item.metrics.total_requests,
                    successful_requests=item.metrics.successful_requests,
                    failure_count=item.metrics.failure_count,
                    accuracy=item.metrics.accuracy,
                    latency_ms=ApiLatencyMetrics(
                        p50=item.metrics.latency_ms.p50,
                        p95=item.metrics.latency_ms.p95,
                        min=item.metrics.latency_ms.min,
                        max=item.metrics.latency_ms.max,
                    ),
                ),
            )
            for item in benchmark_metrics
        ],
    )

    return BenchmarkReport(
        summary=summary,
        generated_at=datetime.now(UTC),
    )
