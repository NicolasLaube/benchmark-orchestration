import typer
import uvicorn

from inference_service.api.app import create_app


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    model: str = "qwen2.5:0.5b",
    rpm: int = 60,
    max_concurrency: int = 4,
    ollama_base_url: str = "http://localhost:11434",
    ollama_timeout_sec: float = 120.0,
    expose_limit_reasons: bool = True,
) -> None:
    app = create_app(
        model=model,
        rpm=rpm,
        max_concurrency=max_concurrency,
        ollama_base_url=ollama_base_url,
        ollama_timeout_sec=ollama_timeout_sec,
        expose_limit_reasons=expose_limit_reasons,
    )

    # The service intentionally runs as a single Uvicorn worker because
    # rate-limit state is stored in process memory.
    uvicorn.run(app, host=host, port=port)


def app_cli() -> None:
    typer.run(run_server)


if __name__ == "__main__":
    app_cli()
