from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    model_name: str = "qwen2.5:0.5b"
    ollama_timeout_sec: float = 120.0

    inference_host: str = "0.0.0.0"
    inference_port: int = 8000

    rpm_limit: int = 60
    max_concurrency: int = 4

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
