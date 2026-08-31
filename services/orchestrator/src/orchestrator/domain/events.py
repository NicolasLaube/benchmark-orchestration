from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class QuestionCompleted:
    run_id: UUID
    question_id: str
    success: bool
    latency_ms: float | None
    attempts: int
    answer: str | None
    error: str | None


@dataclass
class RunCompleted:
    run_id: UUID
    finished_at: datetime
