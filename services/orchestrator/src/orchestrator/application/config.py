from enum import StrEnum

from orchestrator.schedulers.aimd.config import AdaptiveAimdSchedulerConfig
from orchestrator.schedulers.fixed.config import FixedConcurrencySchedulerConfig
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SchedulerMode(StrEnum):
    FIXED = "fixed"
    AIMD = "aimd"


class RunConfig(BaseModel):
    scheduler: FixedConcurrencySchedulerConfig | AdaptiveAimdSchedulerConfig


class Settings(BaseSettings):
    inference_endpoint: str = "http://localhost:8000/infer"

    inference_timeout_seconds: float = Field(
        default=120.0,
        gt=0,
    )

    model_config = SettingsConfigDict(
        env_prefix="ORCHESTRATOR_",
        env_file=".env",
        extra="ignore",
    )
