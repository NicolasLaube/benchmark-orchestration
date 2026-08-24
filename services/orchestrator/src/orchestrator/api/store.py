from enum import StrEnum
from uuid import UUID

from orchestrator.report.models import BenchmarkReport
from pydantic import BaseModel


class RunStatus(StrEnum):
    queued = "queued"
    running = "running"
    finished = "finished"
    failed = "failed"

    def __str__(self):
        return super().__str__()


class RunState(BaseModel):
    run_id: UUID
    status: RunStatus
    report: BenchmarkReport | None = None
    total: int
    completed: int


class RunStore:
    def __init__(self) -> None:
        self._runs: dict[UUID, RunState] = {}

    def create(self, run: RunState) -> None:
        self._runs[run.run_id] = run

    def get(self, run_id: UUID) -> RunState | None:
        return self._runs.get(run_id)

    def update_report(self, run_id: UUID, report: BenchmarkReport) -> None:
        run_state = self.get(run_id)

        run_state.report = report

        run_state.status = RunStatus.finished

        self._runs[run_id] = run_state


run_store = RunStore()
