from fastapi import FastAPI
from orchestrator.api.routes.health import health_router
from orchestrator.api.routes.runs import runs_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Benchmark Orchestrator",
        version="0.1.0",
    )

    app.state["runs"] = {}

    app.include_router(runs_router)
    app.include_router(health_router)

    return app


app = create_app()
