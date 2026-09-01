from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from orchestrator.interfaces.api.routes.health import health_router
from orchestrator.interfaces.api.routes.runs import runs_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Benchmark Orchestrator",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state["runs"] = {}

    app.include_router(runs_router)
    app.include_router(health_router)

    return app


app = create_app()
