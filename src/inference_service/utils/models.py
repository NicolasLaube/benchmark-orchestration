from typing import Literal

from pydantic import BaseModel, Field


class InferRequest(BaseModel):
    question: str = Field(..., min_length=1)


class InferResponse(BaseModel):
    answer: str
    model: str
    latency_ms: int


class ErrorResponse(BaseModel):
    error: str
