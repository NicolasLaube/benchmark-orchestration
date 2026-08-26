from dataclasses import dataclass
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
