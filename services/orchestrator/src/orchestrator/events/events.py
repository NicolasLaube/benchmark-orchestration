from dataclasses import dataclass
from uuid import UUID


@dataclass
class RunStarted:
    run_id: UUID
    total: int


@dataclass
class QuestionCompleted:
    run_id: UUID
    question_id: str
    success: bool
    latency_ms: float


@dataclass
class RunFinished:
    run_id: UUID
