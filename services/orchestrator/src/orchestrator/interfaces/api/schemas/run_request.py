from orchestrator.application.config import SchedulerMode
from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    queue_path: str

    scheduler: SchedulerMode = SchedulerMode.AIMD

    max_concurrency: int = Field(
        default=4,
        ge=1,
    )

    max_target_concurrency: int = Field(
        default=32,
        ge=1,
    )

    max_retries: int = Field(
        default=3,
        ge=0,
    )
