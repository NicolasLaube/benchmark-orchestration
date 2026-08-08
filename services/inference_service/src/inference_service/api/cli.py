import typer
import uvicorn

from inference_service.api.app import create_app


def run_server(
    host: str = typer.Option(default="0.0.0.0", envvar="HOST"),
    port: int = typer.Option(default=8000, envvar="PORT"),
    model: str = typer.Option(default="qwen2.5:0.5b", envvar="MODEL_NAME"),
    rpm: int = typer.Option(60),
    max_concurrency: int = typer.Option(4),
    ollama_base_url: str = typer.Option(
        default="http://localhost:11434",
        envvar="OLLAMA_BASE_URL",
    ),
    ollama_timeout_sec: float = typer.Option(
        default=120.0,
        envvar="OLLAMA_TIMEOUT_SEC",
    ),
    expose_limit_reasons: bool = typer.Option(True),
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
    uvicorn.run(
        app,
        host=host,
        port=port,
        access_log=False,
    )


def app_cli() -> None:
    typer.run(run_server)


if __name__ == "__main__":
    app_cli()
