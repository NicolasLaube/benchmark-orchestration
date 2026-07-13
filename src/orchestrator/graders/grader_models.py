from dataclasses import dataclass


@dataclass(frozen=True)
class GradeResult:
    correct: bool
    score: float
