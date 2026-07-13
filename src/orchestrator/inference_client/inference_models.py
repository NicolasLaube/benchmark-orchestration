"""Output models for inference client."""

from dataclasses import dataclass


@dataclass(frozen=True)
class InferenceResult:
    answer: str
    model: str
    latency_ms: int
