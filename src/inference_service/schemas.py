from pydantic import BaseModel, Field

class InferRequest(BaseModel):
    question: str = Field(..., min_length=1)


class InferResponse(BaseModel):
    answer: str
    model: str
    latency_ms: int


class HealthResponse(BaseModel):
    status: str
    model: str
    rpm_limit: int
    max_concurrency: int


class ErrorResponse(BaseModel):
    error: str